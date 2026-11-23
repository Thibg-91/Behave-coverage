#pragma once

#include <string>

namespace xmlutil {

// Ouvre le fichier XML `filename` avec libxml2, parcourt toutes les balises
// <Interface> du document (quel que soit leur niveau d'imbrication) et compare
// leur contenu texte à `target`.
//
// Retourne true si au moins une balise <Interface> a exactement le contenu
// `target`, false sinon (y compris si le fichier est introuvable ou mal formé).
bool hasInterface(const std::string& filename, const std::string& target);

} // namespace xmlutil
