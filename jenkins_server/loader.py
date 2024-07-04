import jenkins
import time
import xml.etree.ElementTree as ElementTree

from config.loader import reimu_config
from utils.logger import logger


class JenkinsServer:
    def __init__(self):
        self.server = jenkins.Jenkins(" ")
        self.user = "IDK"
        self.version = "IDK"

    def load(self):
        if not reimu_config.ready():
            raise Exception("ruyi-reimu not configured")

        jenkins_cfg = reimu_config.youmu_jenkins["jenkins"]
        self.server = jenkins.Jenkins(jenkins_cfg["host"], jenkins_cfg["username"], jenkins_cfg["password"])
        self.user = self.server.get_whoami()["fullName"]
        logger.info("Login jenkins server with username {}".format(self.user))
        self.version = self.server.get_version()
        logger.info("Jenkins server version {}".format(self.version))

        self._jenkins_folder_create()

        logger.info("Jenkins server check done.\n\n")

    def _jenkins_folder_create(self):
        """
        All jobs in one folder
        """
        job_name = "ruyi-reimu-mugen-auto-test"

        if self.server.job_exists(job_name) and not self.server.is_folder(job_name):
            logger.warn("Jenkins job {} exists but not a folder, delete it".format(job_name))
            logger.warn("Before delete, wait for 6 seconds...")
            time.sleep(6)
            self.server.delete_job(job_name)

        if not self.server.job_exists(job_name):
            logger.info("Create jenkins job folder {}".format(job_name))
            self.server.create_folder(job_name, jenkins.EMPTY_FOLDER_XML)

            xml = self.server.get_job_config(job_name)

            et = ElementTree.fromstring(xml)
            ele = ElementTree.Element("displayName")
            ele.text = "ruyi-reimu mugen 自动化测试"
            et.append(ele)
            ele = ElementTree.Element("description")
            ele.text = "由 ruyi-reimu 生成\n不建议手动修改"
            et.append(ele)

            xml = ElementTree.tostring(et).decode('utf-8')

            logger.info("Configure jenkins job folder {}".format(job_name))
            self.server.reconfig_job(job_name, xml)
        else:
            logger.info("Use existing jenkins job folder {}".format(job_name))


youmu_jenkins = JenkinsServer()
