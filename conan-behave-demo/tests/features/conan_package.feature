Feature: Conan 2 package creation and cache installation
  As a developer
  I want a Behave scenario to build the "mathutils" Conan package and
  install it into the local Conan cache
  So that other projects can consume it as a regular dependency

  Background:
    Given the local Conan cache does not contain "mathutils/1.0.0"

  Scenario: Creating the mathutils package installs it in the local Conan cache
    When I run "conan create" on the "mathutils/1.0.0" package recipe
    Then the "conan create" command should succeed
    And the local Conan cache should contain "mathutils/1.0.0"

  Scenario: A consumer project can build against the cached mathutils package
    When I run "conan create" on the "mathutils/1.0.0" package recipe
    And I install the consumer project dependencies from the local Conan cache
    And I configure and build the consumer project with CMake
    And I run the consumer executable
    Then the consumer output should contain "add(2, 3) = 5"
    And the consumer output should contain "multiply(4, 5) = 20"
