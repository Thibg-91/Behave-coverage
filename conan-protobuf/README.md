# protobuf 5.29.6 (+ abseil 20240116.2) — Conan 1.66, hors-ligne

## Archives à poser à côté des recettes

| Fichier | Dossier | Source |
|---|---|---|
| `abseil-cpp-20240116.2.tar.gz` | `conan-abseil/` | `https://github.com/abseil/abseil-cpp/archive/refs/tags/20240116.2.tar.gz` |
| `protobuf-29.6.tar.gz` | `conan-protobuf/` | `https://github.com/protocolbuffers/protobuf/archive/refs/tags/v29.6.tar.gz` |

Renommer les fichiers téléchargés depuis GitHub (`20240116.2.tar.gz`, `v29.6.tar.gz`). La version Conan de protobuf est celle de la lib C++ (**5.29.6**), le tag GitHub est **v29.6**.

## Profil : `compiler.cppstd` obligatoire

L'ABI d'abseil dépend du standard C++ : abseil, protobuf et l'application doivent utiliser **le même**.

```ini
[settings]
compiler.cppstd=17
```

## Construction

```bash
conan remote disable conancenter          # si inaccessible
cd conan-abseil   && conan create . abseil/20240116.2@ -pr <profil>
cd ../conan-protobuf && conan create . protobuf/5.29.6@ -pr <profil>
```

Options : `-o protobuf:shared=True` (pas sous MSVC), `-o protobuf:with_zlib=True` (nécessite `zlib` sur le remote), `-o abseil:shared=True` (pas sous MSVC).

## Utilisation (CMake)

```cmake
find_package(protobuf REQUIRED CONFIG)
target_link_libraries(app PRIVATE protobuf::libprotobuf)
protobuf_generate(TARGET app LANGUAGE cpp PROTOS ${CMAKE_CURRENT_SOURCE_DIR}/msg.proto)
target_include_directories(app PRIVATE ${CMAKE_CURRENT_BINARY_DIR})
```

Cibles : `protobuf::libprotobuf`, `protobuf::libprotobuf-lite`, `protobuf::libprotoc`, `protobuf::protoc` (exécutable), `absl::*`.

Testé sous Linux/GCC 13 : statique/shared, Release/Debug. Windows/MSVC non testé.
