import os
from conan import ConanFile
from conan.tools.files import copy


class MymathConan(ConanFile):
    name = "mymath"
    version = "1.0"
    description = "Simple math library distributed as pre-built binaries (no Conan build step)."
    license = "MIT"
    # package_type tells Conan this recipe provides a static library
    package_type = "static-library"

    # We only keep os/arch in settings because the binary is pre-compiled
    # outside of Conan. In a production setup you would also track
    # compiler & build_type and ship one package per configuration.
    settings = "os", "arch"

    # No build() method: Conan will never compile anything.
    # "conan export-pkg" is the command used to push the pre-built
    # artefacts into the local cache.

    def package(self):
        """Copy pre-built headers and library into the Conan package folder."""
        src = self.source_folder  # folder that contains this conanfile.py

        copy(self, "*.h",
             src=os.path.join(src, "include"),
             dst=os.path.join(self.package_folder, "include"))

        copy(self, "*.a",   # Linux/macOS static lib
             src=os.path.join(src, "lib"),
             dst=os.path.join(self.package_folder, "lib"))

        copy(self, "*.lib",  # Windows static lib
             src=os.path.join(src, "lib"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        """Describe how consumers should link against this package."""
        self.cpp_info.libs = ["mymath"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
