Feature: Command-line calculator

  As a developer
  I want a calculator binary that evaluates arithmetic expressions
  So that I can verify the core logic through its CLI interface

  Scenario: Addition of two integers
    Given the calculator binary is available
    When I run the calculator with arguments "3" "+" "7"
    Then the output should be "10"

  Scenario: Subtraction yielding a negative result
    Given the calculator binary is available
    When I run the calculator with arguments "5" "-" "12"
    Then the output should be "-7"

  Scenario: Multiplication of two numbers
    Given the calculator binary is available
    When I run the calculator with arguments "6" "*" "7"
    Then the output should be "42"

  Scenario: Floating-point division
    Given the calculator binary is available
    When I run the calculator with arguments "10" "/" "4"
    Then the output should be "2.5"

  Scenario: Division by zero returns an error
    Given the calculator binary is available
    When I run the calculator with arguments "9" "/" "0"
    Then the exit code should be non-zero
    And the error output should contain "Division by zero"
