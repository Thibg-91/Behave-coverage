#include <cstdlib>
#include <iostream>

#include "mqtt/async_client.h"
#include "mqtt/client.h"

int main()
{
    std::cout << mqtt::PAHO_MQTTPP_VERSION_STR << std::endl;

    try {
        // Aucune connexion reseau : on verifie que l'API se lie et s'execute
        mqtt::async_client async_cli("tcp://localhost:1883", "conan-test-async");
        mqtt::client sync_cli("tcp://localhost:1883", "conan-test-sync");

        auto conn_opts = mqtt::connect_options_builder()
                             .clean_session()
                             .automatic_reconnect(false)
                             .finalize();

        auto msg = mqtt::make_message("conan/test", "hello", 1, false);

        std::cout << "client id : " << async_cli.get_client_id() << "\n"
                  << "topic     : " << msg->get_topic() << "\n"
                  << "payload   : " << msg->to_string() << "\n"
                  << "connecte  : " << std::boolalpha << async_cli.is_connected()
                  << std::endl;
        (void)conn_opts;
        (void)sync_cli;
    }
    catch (const mqtt::exception& e) {
        std::cerr << "Erreur MQTT : " << e.what() << std::endl;
        return EXIT_FAILURE;
    }

    std::cout << "paho-mqtt-cpp OK" << std::endl;
    return EXIT_SUCCESS;
}
