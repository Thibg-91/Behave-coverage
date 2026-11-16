#include <cstdlib>
#include <iostream>
#include <string>

#include <google/protobuf/stubs/common.h>
#include <google/protobuf/util/json_util.h>

#include "person.pb.h"

int main()
{
    GOOGLE_PROTOBUF_VERIFY_VERSION;
    std::cout << "protobuf " << google::protobuf::internal::VersionString(GOOGLE_PROTOBUF_VERSION)
              << std::endl;

    demo::Person person;
    person.set_name("Ada");
    person.set_id(42);
    person.add_emails("ada@example.org");
    person.mutable_created()->set_seconds(1700000000);

    // Binaire : aller-retour
    std::string wire;
    if (!person.SerializeToString(&wire)) return EXIT_FAILURE;
    demo::Person decoded;
    if (!decoded.ParseFromString(wire) || decoded.id() != 42) {
        std::cerr << "aller-retour binaire KO" << std::endl;
        return EXIT_FAILURE;
    }

    // JSON (libprotobuf complete + abseil)
    std::string json;
    auto status = google::protobuf::util::MessageToJsonString(decoded, &json);
    if (!status.ok()) {
        std::cerr << "JSON KO : " << status << std::endl;
        return EXIT_FAILURE;
    }
    std::cout << "binaire : " << wire.size() << " octets\n"
              << "json    : " << json << std::endl;

    google::protobuf::ShutdownProtobufLibrary();
    std::cout << "protobuf OK" << std::endl;
    return EXIT_SUCCESS;
}
