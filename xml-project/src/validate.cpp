#include <libxml/parser.h>
#include <libxml/uri.h>
#include <libxml/xinclude.h>
#include <libxml/xmlschemas.h>
#include <libxml/xpath.h>
#include <libxml/xpathInternals.h>

#include <cstdarg>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <string>
#include <unistd.h>
#include <vector>

// ---------------------------------------------------------------------------
// Compteur d'erreurs pour la passe en cours
// ---------------------------------------------------------------------------
static int g_errorCount = 0;

// ---------------------------------------------------------------------------
// Retrouve la colonne (1-based) du premier '<' sur la ligne donnée.
// Compensé le fait que libxml2 ne stocke pas la colonne dans les nœuds
// après le parsing : err->int2 == 0 pour les erreurs de validation XSD.
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
            for (int col = 0; col < (int)line.size(); ++col)
                if (line[col] == '<') return col + 1;
            return 0;
        }
    }
    return 0;
}

// ---------------------------------------------------------------------------
// Callback structuré — appelé par libxml2 pour chaque erreur de validation.
// ---------------------------------------------------------------------------
static void onValidationError(void* /*ctx*/, xmlErrorPtr err)
{
    ++g_errorCount;
    const char* file = err->file ? err->file : "(inconnu)";
    int col = err->int2;
    if (col == 0) col = findColumn(file, err->line);

    std::cerr << "\n[ERREUR] fichier  : " << file
              << "\n         ligne    : " << err->line;
    if (col > 0) std::cerr << "  |  colonne : " << col;
    std::cerr << "\n         message  : "
              << (err->message ? err->message : "(aucun)") << "\n";
}

static void onSchemaParserError(void* /*ctx*/, const char* fmt, ...)
{
    va_list ap; va_start(ap, fmt);
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
// Valide un fichier XML (déjà parsé) contre un schéma XSD.
// err->file correspond à xmlPath, ce qui garantit une localisation exacte.
// ---------------------------------------------------------------------------
static int validateDoc(xmlDocPtr doc, const char* xsdPath)
{
    xmlSchemaPtr schema = loadSchema(xsdPath);
    if (!schema) {
        std::cerr << "  Erreur : impossible de charger '" << xsdPath << "'\n";
        return -1;
    }
    g_errorCount = 0;
    xmlSchemaValidCtxtPtr vctx = xmlSchemaNewValidCtxt(schema);
    xmlSchemaSetValidStructuredErrors(vctx, onValidationError, nullptr);
    xmlSchemaValidateDoc(vctx, doc);
    int errors = g_errorCount;
    xmlSchemaFreeValidCtxt(vctx);
    xmlSchemaFree(schema);
    return errors;
}

// ---------------------------------------------------------------------------
// Parcourt les éléments xi:include du document et retourne la liste des
// chemins résolus des fichiers inclus.
//
// La résolution se fait via xmlBuildURI(href, baseURI) où baseURI est l'URL
// absolue du document principal (garantie par xmlReadFile avec un chemin
// absolu ou par conversion préalable).
// ---------------------------------------------------------------------------
static std::vector<std::string> discoverIncludes(xmlDocPtr doc)
{
    std::vector<std::string> paths;

    xmlXPathContextPtr xpctx = xmlXPathNewContext(doc);
    if (!xpctx) return paths;

    xmlXPathRegisterNs(xpctx,
                       BAD_CAST "xi",
                       BAD_CAST "http://www.w3.org/2001/XInclude");

    xmlXPathObjectPtr result =
        xmlXPathEvalExpression(BAD_CAST "//xi:include[@href]", xpctx);

    if (result && result->nodesetval) {
        for (int i = 0; i < result->nodesetval->nodeNr; ++i) {
            xmlNodePtr node = result->nodesetval->nodeTab[i];
            xmlChar* href   = xmlGetProp(node, BAD_CAST "href");
            if (!href) continue;

            // Résoudre href par rapport à l'URL de base du document
            xmlChar* base   = xmlNodeGetBase(doc, node);
            xmlChar* absUri = xmlBuildURI(href, base);

            if (absUri)
                paths.emplace_back(reinterpret_cast<char*>(absUri));

            if (absUri) xmlFree(absUri);
            if (base)   xmlFree(base);
            xmlFree(href);
        }
    }

    if (result) xmlXPathFreeObject(result);
    xmlXPathFreeContext(xpctx);
    return paths;
}

// ---------------------------------------------------------------------------
// Détermine le schéma à utiliser pour un fichier XML inclus.
// Convention : le schéma se nomme {elementRacine}.xsd dans schemasDir.
// Si le fichier n'existe pas, retourne une chaîne vide.
// ---------------------------------------------------------------------------
static std::string findSchemaFor(xmlDocPtr doc, const std::string& schemasDir)
{
    xmlNodePtr root = xmlDocGetRootElement(doc);
    if (!root || !root->name) return "";

    std::string candidate = schemasDir + "/"
                          + reinterpret_cast<const char*>(root->name)
                          + ".xsd";

    return (access(candidate.c_str(), R_OK) == 0) ? candidate : "";
}

// ---------------------------------------------------------------------------
int main(int argc, char* argv[])
{
    // Utiliser un chemin absolu afin que xmlBuildURI puisse résoudre les
    // href relatifs des xi:include par rapport au bon répertoire.
    char* cwd = getcwd(nullptr, 0);
    std::string mainXml = cwd ? std::string(cwd) + "/" : "./";
    free(cwd);
    mainXml   += (argc > 1) ? argv[1] : "data/library.xml";
    const char* mainXsd = (argc > 2) ? argv[2] : "schemas/library.xsd";

    // Déduire le répertoire des schémas depuis le chemin du schéma principal
    std::string schemasDir = mainXsd;
    size_t slash = schemasDir.rfind('/');
    schemasDir = (slash != std::string::npos) ? schemasDir.substr(0, slash) : ".";

    std::cout << "=== Validation XML/XSD avec libxml2 ===\n"
              << "  Document : " << mainXml << "\n"
              << "  Schema   : " << mainXsd << "\n\n";

    // -----------------------------------------------------------------------
    // Etape 1 : lire le document principal SANS traiter les XInclude
    //           pour pouvoir inspecter les xi:include avant fusion.
    // -----------------------------------------------------------------------
    xmlDocPtr mainDoc = xmlReadFile(mainXml.c_str(), nullptr,
                                    XML_PARSE_NOENT | XML_PARSE_NONET);
    if (!mainDoc) {
        std::cerr << "Erreur : impossible de lire '" << mainXml << "'\n";
        return 1;
    }

    // -----------------------------------------------------------------------
    // Etape 2 : découvrir les fichiers inclus via XPath sur xi:include
    // -----------------------------------------------------------------------
    std::vector<std::string> includes = discoverIncludes(mainDoc);

    if (includes.empty()) {
        std::cout << "Aucun xi:include détecté dans le document.\n";
    } else {
        std::cout << includes.size() << " fichier(s) inclus détecté(s).\n\n";
    }

    int totalErrors = 0;
    int step        = 1;
    int totalSteps  = (int)includes.size() + 1;  // inclus + document principal

    // -----------------------------------------------------------------------
    // Etape 3 : valider chaque fichier inclus indépendamment
    //           => err->file pointe sur le fichier inclus réel (ligne + col)
    // -----------------------------------------------------------------------
    for (const std::string& absPath : includes) {
        std::cout << "[" << step++ << "/" << totalSteps << "] "
                  << "Validation du fichier inclus\n"
                  << "  Fichier : " << absPath << "\n";

        xmlDocPtr subDoc = xmlReadFile(absPath.c_str(), nullptr,
                                       XML_PARSE_NOENT | XML_PARSE_NONET);
        if (!subDoc) {
            std::cerr << "  Erreur : impossible de lire '" << absPath << "'\n";
            ++totalErrors;
            continue;
        }

        std::string schema = findSchemaFor(subDoc, schemasDir);
        if (schema.empty()) {
            std::cout << "  Schema  : (introuvable — validation ignorée)\n\n";
            xmlFreeDoc(subDoc);
            continue;
        }
        std::cout << "  Schema  : " << schema << "\n";

        int errors = validateDoc(subDoc, schema.c_str());
        xmlFreeDoc(subDoc);

        totalErrors += (errors > 0) ? errors : 0;
        std::cout << (errors == 0
                          ? "\n  Resultat : VALIDE\n\n"
                          : "\n  Resultat : INVALIDE  (" + std::to_string(errors) + " erreur(s))\n\n");
    }

    // -----------------------------------------------------------------------
    // Etape 4 : traiter XInclude puis valider le document fusionné
    //           => vérifie la cohérence structurelle globale
    // -----------------------------------------------------------------------
    std::cout << "[" << step << "/" << totalSteps << "] "
              << "Validation du document principal (après XInclude)\n"
              << "  Fichier : " << mainXml << "\n"
              << "  Schema  : " << mainXsd << "\n";

    int xiCount = xmlXIncludeProcess(mainDoc);
    if (xiCount < 0) {
        std::cerr << "  Erreur XInclude\n";
        ++totalErrors;
    } else {
        std::cout << "  XInclude : " << xiCount << " substitution(s)\n";

        int errors = validateDoc(mainDoc, mainXsd);
        totalErrors += (errors > 0) ? errors : 0;
        std::cout << (errors == 0
                          ? "\n  Resultat : VALIDE\n"
                          : "\n  Resultat : INVALIDE  (" + std::to_string(errors) + " erreur(s))\n");
    }

    xmlFreeDoc(mainDoc);
    xmlCleanupParser();

    std::cout << "\n" << std::string(40, '=') << "\n"
              << (totalErrors == 0 ? "Tout est valide." : "Validation echouee.") << "\n";

    return (totalErrors > 0) ? 1 : 0;
}
