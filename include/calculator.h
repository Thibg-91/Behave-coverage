#pragma once

#include <stdexcept>
#include <string>

namespace calc {

double add(double a, double b);
double subtract(double a, double b);
double multiply(double a, double b);
double divide(double a, double b);  // throws std::invalid_argument on zero divisor

// Parse and evaluate a simple expression: <number> <op> <number>
// Supported ops: +  -  *  /
// Returns result as double, throws on invalid input or division by zero
double evaluate(const std::string& a, const std::string& op, const std::string& b);

} // namespace calc
