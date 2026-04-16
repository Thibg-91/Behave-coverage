#include <iostream>
#include "mymath.h"

int main() {
    int a = 7;
    int b = 5;
    int result = mymath::add(a, b);
    std::cout << a << " + " << b << " = " << result << std::endl;
    return 0;
}
