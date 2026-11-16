#include <cstdlib>
#include <iostream>
#include <string>

#include "absl/container/flat_hash_map.h"
#include "absl/log/log.h"
#include "absl/strings/str_cat.h"
#include "absl/strings/str_format.h"
#include "absl/strings/str_split.h"
#include "absl/time/clock.h"

int main()
{
    absl::flat_hash_map<std::string, int> counts;
    for (absl::string_view word : absl::StrSplit("a,b,a,c,a", ','))
        ++counts[std::string(word)];

    std::cout << absl::StrCat("a=", counts["a"], " b=", counts["b"]) << "\n"
              << absl::StrFormat("%s v%d", "abseil", 20240116) << "\n"
              << "now: " << absl::FormatTime(absl::Now()) << std::endl;

    if (counts["a"] != 3) {
        LOG(ERROR) << "flat_hash_map KO";
        return EXIT_FAILURE;
    }
    std::cout << "abseil OK" << std::endl;
    return EXIT_SUCCESS;
}
