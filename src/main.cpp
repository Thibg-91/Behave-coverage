#include "calculator.h"

#include <iostream>
#include <cstdlib>

int main(int argc, char* argv[]) {
    if (argc != 4) {
        std::cerr << "Usage: " << argv[0] << " <number> <op> <number>" << std::endl;
        std::cerr << "  Supported operators: + - * /" << std::endl;
        return EXIT_FAILURE;
    }

    try {
        double result = calc::evaluate(argv[1], argv[2], argv[3]);

        // Print integer representation when there is no fractional part
        if (result == static_cast<long long>(result)) {
            std::cout << static_cast<long long>(result) << std::endl;
        } else {
            std::cout << result << std::endl;
        }
    } catch (const std::invalid_argument& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return EXIT_FAILURE;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
}
