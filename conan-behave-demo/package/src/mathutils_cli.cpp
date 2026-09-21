#include <cstdlib>
#include <iostream>

#include "mathutils/mathutils.hpp"

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: mathutils-cli <a> <b>\n";
        return 1;
    }

    int a = std::atoi(argv[1]);
    int b = std::atoi(argv[2]);

    std::cout << "add(" << a << ", " << b << ") = " << mathutils::add(a, b) << "\n";
    std::cout << "multiply(" << a << ", " << b << ") = " << mathutils::multiply(a, b) << "\n";
    return 0;
}
