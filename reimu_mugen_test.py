#!/usr/bin/env python3

from config.loader import reimu_config
from jenkins_controller.server import youmu_jenkins

if __name__ == "__main__":
    reimu_config.load()
    youmu_jenkins.load()
    youmu_jenkins.test()

