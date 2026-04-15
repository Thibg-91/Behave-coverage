from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MyAppConan(ConanFile):
    name = "myapp"
    version = "1.0"
    description = "Simple executable that uses the mymath pre-built library."
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    # Declare the dependency on mymath
    requires = "mymath/1.0"

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
