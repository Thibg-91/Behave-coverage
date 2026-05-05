#include <libxml/parser.h>
#include <libxml/xmlschemas.h>
#include <libxml/xinclude.h>

#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>

// ---------------------------------------------------------------------------
// Compteur d'erreurs pour la passe en cours
// ---------------------------------------------------------------------------
static int g_errorCount = 0;

// ---------------------------------------------------------------------------
// Retrouve la colonne (1-based) du premier '<' sur la ligne donnée d'un
// fichier texte.  Utilisé pour compenser l'absence de tracking de colonne
// dans libxml2 après la phase de parsing (err->int2 vaut 0 pour les erreurs
// de validation XSD).
// ---------------------------------------------------------------------------
static int findColumn(const char* filePath, int targetLine)
{
    if (!filePath || targetLine <= 0)
        return 0;

    std::ifstream f(filePath);
    if (!f.is_open())
        return 0;

    std::string line;
    for (int n = 1; std::getline(f, line); ++n) {
        if (n == targetLine) {
            for (int col = 0; col < (int)line.size(); ++col) {
                if (line[col] == '<')
                    return col + 1;  // 1-based
            }
            return 0;
        }
    }
    return 0;
}

// ---------------------------------------------------------------------------
// Callback structuré — appelé par libxml2 pour chaque erreur de validation.
//
// Quand le document est validé directement (sans fusion XInclude), err->file
// contient l'URL du fichier source réel.  La colonne n'est pas disponible
// via err->int2 (toujours 0 pour la validation XSD) ; on la retrouve en
// relisant la ligne correspondante du fichier source.
// ---------------------------------------------------------------------------
static void onValidationError(void* /*ctx*/, xmlErrorPtr err)
{
    ++g_errorCount;

    const char* file = err->file ? err->file : "(inconnu)";
    int line         = err->line;

    // Priorité à err->int2 (colonne du parseur), sinon lookup dans le source
    int col = err->int2;
    if (col == 0)
        col = findColumn(file, line);

    std::cerr << "\n[ERREUR] fichier  : " << file
              << "\n         ligne    : " << line;

    if (col > 0)
        std::cerr << "  |  colonne : " << col;

    std::cerr << "\n         message  : "
              << (err->message ? err->message : "(aucun)") << "\n";
}

// Redirige les erreurs de parsing de schéma vers stderr
static void onSchemaParserError(void* /*ctx*/, const char* fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
}

// ---------------------------------------------------------------------------
static xmlSchemaPtr loadSchema(const char* xsdPath)
{
    xmlSchemaParserCtxtPtr pctx = xmlSchemaNewParserCtxt(xsdPath);
    if (!pctx) return nullptr;
    xmlSchemaSetParserErrors(pctx,
                             onSchemaParserError, onSchemaParserError, nullptr);
    xmlSchemaPtr schema = xmlSchemaParse(pctx);
    xmlSchemaFreeParserCtxt(pctx);
    return schema;
}

// ---------------------------------------------------------------------------
// Valide un fichier XML contre un schéma XSD.
// err->file correspond directement à xmlPath : les erreurs indiquent le
// fichier source réel avec son numéro de ligne et la colonne reconstituée.
// Retourne le nombre d'erreurs trouvées, -1 en cas d'erreur interne.
// ---------------------------------------------------------------------------
static int validateDocument(const char* xmlPath, const char* xsdPath)
{
    xmlDocPtr doc = xmlReadFile(xmlPath, nullptr, XML_PARSE_NOENT | XML_PARSE_NONET);
    if (!doc) {
        std::cerr << "  Erreur : impossible de lire '" << xmlPath << "'\n";
        return -1;
    }

    xmlSchemaPtr schema = loadSchema(xsdPath);
    if (!schema) {
        std::cerr << "  Erreur : impossible de charger '" << xsdPath << "'\n";
        xmlFreeDoc(doc);
        return -1;
    }

    g_errorCount = 0;
    xmlSchemaValidCtxtPtr vctx = xmlSchemaNewValidCtxt(schema);
    xmlSchemaSetValidStructuredErrors(vctx, onValidationError, nullptr);
    xmlSchemaValidateDoc(vctx, doc);
    int errors = g_errorCount;

    xmlSchemaFreeValidCtxt(vctx);
    xmlSchemaFree(schema);
    xmlFreeDoc(doc);
    return errors;
}

// ---------------------------------------------------------------------------
// Valide un document XML en traitant d'abord les directives XInclude.
// Après fusion, err->file pointe sur le document racine ; la colonne est
// reconstituée via findColumn() sur le fichier racine (approximation pour
// les éléments issus de fichiers inclus — utiliser l'étape 1 pour le
// diagnostic précis des fichiers inclus).
// ---------------------------------------------------------------------------
static int validateWithXInclude(const char* xmlPath, const char* xsdPath)
{
    xmlDocPtr doc = xmlReadFile(xmlPath, nullptr, XML_PARSE_NOENT | XML_PARSE_NONET);
    if (!doc) {
        std::cerr << "  Erreur : impossible de lire '" << xmlPath << "'\n";
        return -1;
    }

    int xiCount = xmlXIncludeProcess(doc);
    if (xiCount < 0) {
        std::cerr << "  Erreur XInclude dans '" << xmlPath << "'\n";
        xmlFreeDoc(doc);
        return -1;
    }
    std::cout << "  XInclude : " << xiCount << " substitution(s)\n";

    xmlSchemaPtr schema = loadSchema(xsdPath);
    if (!schema) {
        std::cerr << "  Erreur : impossible de charger '" << xsdPath << "'\n";
        xmlFreeDoc(doc);
        return -1;
    }

    g_errorCount = 0;
    xmlSchemaValidCtxtPtr vctx = xmlSchemaNewValidCtxt(schema);
    xmlSchemaSetValidStructuredErrors(vctx, onValidationError, nullptr);
    xmlSchemaValidateDoc(vctx, doc);
    int errors = g_errorCount;

    xmlSchemaFreeValidCtxt(vctx);
    xmlSchemaFree(schema);
    xmlFreeDoc(doc);
    return errors;
}

// ---------------------------------------------------------------------------
int main(int argc, char* argv[])
{
    const char* mainXml  = (argc > 1) ? argv[1] : "data/library.xml";
    const char* mainXsd  = (argc > 2) ? argv[2] : "schemas/library.xsd";
    const char* booksXml = "data/books.xml";
    const char* booksXsd = "schemas/book.xsd";

    std::cout << "=== Validation XML/XSD avec libxml2 ===\n";

    // -----------------------------------------------------------------------
    // Etape 1 : valider le fichier inclus de façon autonome.
    //   err->file = books.xml -> fichier source exact, ligne et colonne.
    // -----------------------------------------------------------------------
    std::cout << "\n[1/2] Validation du fichier inclus\n"
              << "  XML    : " << booksXml << "\n"
              << "  Schema : " << booksXsd << "\n";

    int booksErrors = validateDocument(booksXml, booksXsd);
    std::cout << (booksErrors == 0
                      ? "\n  Resultat : VALIDE\n"
                      : "\n  Resultat : INVALIDE  (" + std::to_string(booksErrors) + " erreur(s))\n");

    // -----------------------------------------------------------------------
    // Etape 2 : valider le document principal après traitement XInclude.
    //   Vérifie la structure globale (library > name + books).
    //   Note : après fusion XInclude, err->file pointe sur library.xml ;
    //   libxml2 < 2.13 ne positionne pas xml:base sur les noeuds inclus.
    //   La colonne est reconstituée via findColumn() sur le fichier racine.
    // -----------------------------------------------------------------------
    std::cout << "\n[2/2] Validation du document principal (avec XInclude)\n"
              << "  XML    : " << mainXml << "\n"
              << "  Schema : " << mainXsd << "\n";

    int mainErrors = validateWithXInclude(mainXml, mainXsd);
    std::cout << (mainErrors == 0
                      ? "\n  Resultat : VALIDE\n"
                      : "\n  Resultat : INVALIDE  (" + std::to_string(mainErrors) + " erreur(s))\n");

    // -----------------------------------------------------------------------
    std::cout << "\n" << std::string(40, '=') << "\n";
    int total = booksErrors + mainErrors;
    std::cout << (total == 0 ? "Tout est valide." : "Validation echouee.") << "\n";

    xmlCleanupParser();
    return (total > 0) ? 1 : 0;
}
