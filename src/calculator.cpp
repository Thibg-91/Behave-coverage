#include "calculator.h"

#include <stdexcept>
#include <string>

namespace calc {

double add(double a, double b) {
    return a + b;
}

double subtract(double a, double b) {
    return a - b;
}

double multiply(double a, double b) {
    return a * b;
}

double divide(double a, double b) {
    if (b == 0.0) {
        throw std::invalid_argument("Division by zero");
    }
    return a / b;
}

double evaluate(const std::string& sa, const std::string& op, const std::string& sb) {
    double a = std::stod(sa);
    double b = std::stod(sb);

    if (op == "+") return add(a, b);
    if (op == "-") return subtract(a, b);
    if (op == "*") return multiply(a, b);
    if (op == "/") return divide(a, b);

    throw std::invalid_argument("Unknown operator: " + op);
}

} // namespace calc
