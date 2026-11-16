#include <stdio.h>
#include <stdlib.h>

#ifdef PAHO_TEST_ASYNC
#  include "MQTTAsync.h"
#  define get_version_info MQTTAsync_getVersionInfo
typedef MQTTAsync_nameValue name_value;
#else
#  include "MQTTClient.h"
#  define get_version_info MQTTClient_getVersionInfo
typedef MQTTClient_nameValue name_value;
#endif

int main(void)
{
    int rc;
    name_value* info = get_version_info();

    for (; info && info->name; ++info)
        printf("%s: %s\n", info->name, info->value);

    /* Aucune connexion reseau : on verifie juste que l'API se lie et s'execute */
#ifdef PAHO_TEST_ASYNC
    MQTTAsync client;
    rc = MQTTAsync_create(&client, "tcp://localhost:1883", "conan-test",
                          MQTTCLIENT_PERSISTENCE_NONE, NULL);
    if (rc != MQTTASYNC_SUCCESS) {
        printf("MQTTAsync_create a echoue : %d\n", rc);
        return EXIT_FAILURE;
    }
    MQTTAsync_destroy(&client);
#else
    MQTTClient client;
    rc = MQTTClient_create(&client, "tcp://localhost:1883", "conan-test",
                           MQTTCLIENT_PERSISTENCE_NONE, NULL);
    if (rc != MQTTCLIENT_SUCCESS) {
        printf("MQTTClient_create a echoue : %d\n", rc);
        return EXIT_FAILURE;
    }
    MQTTClient_destroy(&client);
#endif

    printf("paho-mqtt-c OK\n");
    return EXIT_SUCCESS;
}
