#include "xml_interface.h"

#include <libxml/parser.h>
#include <libxml/tree.h>

#include <memory>
#include <string>

namespace xmlutil {

namespace {

// RAII : libération automatique des ressources libxml2
struct XmlDocDeleter {
    void operator()(xmlDoc* doc) const { xmlFreeDoc(doc); }
};
using XmlDocPtr = std::unique_ptr<xmlDoc, XmlDocDeleter>;

struct XmlCharDeleter {
    void operator()(xmlChar* str) const { xmlFree(str); }
};
using XmlCharPtr = std::unique_ptr<xmlChar, XmlCharDeleter>;

bool isInterfaceNode(const xmlNode* node) {
    return node->type == XML_ELEMENT_NODE &&
           xmlStrEqual(node->name, BAD_CAST "Interface");
}

// Parcours en profondeur de l'arbre à partir de `node`
bool findInterface(const xmlNode* node, const std::string& target) {
    for (const xmlNode* cur = node; cur != nullptr; cur = cur->next) {
        if (isInterfaceNode(cur)) {
            XmlCharPtr content(xmlNodeGetContent(cur));
            if (content && target == reinterpret_cast<const char*>(content.get())) {
                return true;
            }
        }
        if (cur->children && findInterface(cur->children, target)) {
            return true;
        }
    }
    return false;
}

} // namespace

bool hasInterface(const std::string& filename, const std::string& target) {
    // XML_PARSE_NONET : pas d'accès réseau ; NOERROR/NOWARNING : pas de sortie
    // sur stderr, un fichier invalide renvoie simplement false.
    XmlDocPtr doc(xmlReadFile(filename.c_str(), nullptr,
                              XML_PARSE_NONET | XML_PARSE_NOERROR | XML_PARSE_NOWARNING));
    if (!doc) {
        return false;
    }

    const xmlNode* root = xmlDocGetRootElement(doc.get());
    return root != nullptr && findInterface(root, target);
}

} // namespace xmlutil
