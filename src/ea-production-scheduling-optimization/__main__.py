import logging
import sys
import time

# See README before using
# from util.vault_helper import VaultHelper
# from util.keytab_helper import KeytabHelper

kill_now = False
logger = logging.getLogger("ea_production_scheduling_optimization")
logger.setLevel(logging.DEBUG)
log_formatter = logging.Formatter(
    "%(asctime)s [%(processName)-16.16s] [%(levelname)-5.5s]  %(message)s"
)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(log_formatter)
logger.addHandler(handler)


"""
The main python app should run continuously for the container/pod
to stay up in Kubernetes. You can achieve this by using a while loop
that is either always true or looks for some condition to be met.
For example:
while True:
OR
while os.path.exists("/path/to/runtime/file"):
"""
if __name__ == "__main__":
    """
    Vault Helper
    REQUIRES: Vault Setup (See README)
    """
    # vh = VaultHelper(null, ea_production_scheduling_optimization)
    # test_secret = vh.get_secret("testSecret")
    """
    Keytab Helper
    To use in lieu of sidecar container. You would place the check_keytab
    somewhere in your while loop where it will check the keytab regularly

    REQUIRES: Vault Setup and MID (See README)
    """
    # kh = KeytabHelper(vh, "miduser_secret_key", "midpassword_secret_key", "/path/to/keytab_file_location")

    logger.debug("Starting job")
    while not kill_now:
        try:
            logger.debug("Hello World!")
            # kh.check_keytab()
            time.sleep(10)
        except KeyboardInterrupt:
            logger.info("Exiting due to SIGINT")
            kill_now = True
