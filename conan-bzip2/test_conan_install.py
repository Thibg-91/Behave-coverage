#!/usr/bin/env python3
"""
Test: conan install de bzip2 sans --build=missing.

- Sur cette machine (Linux/GCC) : un profil natif est auto-détecté.
- Sur la machine cible (Windows/MSVC 192) : utiliser -pr profiles/msvc192-release.profile.

Le test est ignoré (SKIP) si ConanCenter est injoignable (réseau restreint / proxy).
"""
import os
import socket
import subprocess
import tempfile
import unittest

CONANFILE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_PROFILE_NAME = "_conan_bzip2_test_profile"
CONAN_CENTER_HOST = "center2.conan.io"
CONAN_CENTER_PORT = 443


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def is_conan_center_reachable() -> bool:
    """Vérifie la connectivité TCP vers ConanCenter (timeout 5 s)."""
    try:
        with socket.create_connection((CONAN_CENTER_HOST, CONAN_CENTER_PORT), timeout=5):
            return True
    except OSError:
        return False


class TestConanInstall(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Crée un profil natif dédié aux tests (détection automatique)."""
        result = run([
            "conan", "profile", "detect",
            "--name", TEST_PROFILE_NAME,
            "--force",
        ])
        if result.returncode != 0:
            raise RuntimeError(
                f"Impossible de créer le profil de test :\n{result.stderr}"
            )
        print(f"\n[setup] Profil '{TEST_PROFILE_NAME}' créé :")
        # Affiche le profil détecté pour information
        info = run(["conan", "profile", "show", "--profile:host", TEST_PROFILE_NAME])
        print(info.stdout)

    @classmethod
    def tearDownClass(cls):
        """Supprime le profil de test après exécution."""
        profiles_dir = os.path.expanduser("~/.conan2/profiles")
        profile_path = os.path.join(profiles_dir, TEST_PROFILE_NAME)
        if os.path.exists(profile_path):
            os.remove(profile_path)
            print(f"\n[teardown] Profil '{TEST_PROFILE_NAME}' supprimé.")

    def test_install_bzip2_no_build_missing(self):
        """
        conan install doit réussir en utilisant uniquement les binaires
        précompilés de ConanCenter (pas de --build=missing).
        """
        if not is_conan_center_reachable():
            self.skipTest(
                f"ConanCenter ({CONAN_CENTER_HOST}:{CONAN_CENTER_PORT}) injoignable "
                "depuis cet environnement (réseau restreint / proxy). "
                "Relancez le test depuis un poste avec accès à ConanCenter."
            )

        with tempfile.TemporaryDirectory() as build_dir:
            cmd = [
                "conan", "install", CONANFILE_DIR,
                "--output-folder", build_dir,
                "--profile:host", TEST_PROFILE_NAME,
                "--profile:build", TEST_PROFILE_NAME,
                # Pas de --build=missing : on exige des binaires précompilés.
            ]
            print(f"\n[test] Commande : {' '.join(cmd)}")
            result = run(cmd)

            print("--- stdout ---")
            print(result.stdout)
            if result.returncode != 0:
                print("--- stderr ---")
                print(result.stderr)

            self.assertEqual(
                result.returncode, 0,
                msg=(
                    f"conan install a échoué (rc={result.returncode}).\n"
                    f"stderr:\n{result.stderr}"
                ),
            )

            # Vérifie qu'un fichier CMake pour bzip2 a bien été généré
            generated = os.listdir(build_dir)
            bzip2_files = [
                f for f in generated
                if "bzip2" in f.lower() or "BZip2" in f
            ]
            self.assertTrue(
                bzip2_files,
                msg=(
                    "Aucun fichier CMake lié à bzip2 trouvé dans le dossier de sortie.\n"
                    f"Fichiers générés : {generated}"
                ),
            )
            print(f"\n[test] Fichiers bzip2 générés : {bzip2_files}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
