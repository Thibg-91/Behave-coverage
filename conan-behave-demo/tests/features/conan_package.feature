Feature: Conan 2 package creation and cache consumption via VirtualRunEnv
  As a developer
  I want a Behave scenario to build the "mathutils" Conan package,
  install it into the local Conan cache, then consume it straight from
  the cache using a generated Conan virtual run environment script
  So that I don't need to rebuild or relink anything to use the package

  Background:
    Given the local Conan cache does not contain "mathutils/1.0.0"
    When I run "conan create" on the "mathutils/1.0.0" package recipe
    Then the "conan create" command should succeed
    And the local Conan cache should contain "mathutils/1.0.0"

  Scenario: Running the packaged CLI tool directly fails without the virtual run environment
    When I try to run "mathutils-cli" straight from the Conan cache without any environment script
    Then it should fail because "libmathutils.so" cannot be found

  Scenario: Generating a VirtualRunEnv script allows consuming the package already in cache
    When I generate the Conan virtual run environment for "mathutils/1.0.0"
    Then a "conanrun.sh" script should have been generated
    When I run "mathutils-cli 2 3" using the generated virtual run environment
    Then the command should succeed
    And the output should contain "add(2, 3) = 5"
    And the output should contain "multiply(2, 3) = 6"
