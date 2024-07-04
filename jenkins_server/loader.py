import jenkins
import time
import xml.etree.ElementTree as ElementTree

from config.loader import reimu_config
from utils.errors import AssertException
from utils.logger import logger


class JenkinsServer:
    FOLDER_NAME = "ruyi-reimu-mugen-auto-test"

    def __init__(self):
        self.server = jenkins.Jenkins(" ")
        self.user = "IDK"
        self.version = "IDK"

        self._host = ""
        self._username = ""
        self._password = ""

        self.clouds = {}
        self.nodes = {}
        self.test_platforms = {}

    def load(self):
        if not reimu_config.ready():
            raise Exception("ruyi-reimu not configured")

        jenkins_cfg = reimu_config.youmu_jenkins["jenkins"]
        self._host = jenkins_cfg["host"]
        self._username = jenkins_cfg["username"]
        self._password = jenkins_cfg["password"]

        self._new_server()

        self.user = self.server.get_whoami()["fullName"]
        logger.info("Login jenkins server with username {}".format(self.user))
        self.version = self.server.get_version()
        logger.info("Jenkins server version {}".format(self.version))

        self._jenkins_folder_create()

        # Clouds/nodes info
        clouds = reimu_config.youmu_jenkins["jenkins"]["clouds"]
        test = reimu_config.youmu_jenkins["test_platforms"]
        if not isinstance(clouds, list):
            raise AssertException("jenkins.clouds not a list type")
        if not isinstance(test, dict):
            raise AssertException("jenkins.test_platforms not a dist type")
        for p in test.items():
            self.test_platforms[p[0]] = {"labels": p[1]}

        for c in clouds:
            nodes = []
            for a in reimu_config.youmu_jenkins["agent_"+c]:
                labels = []
                nodes.append(a["name"])
                for lb in self.server.get_node_info(a["name"])["assignedLabels"]:
                    labels.append(lb["name"])
                self.nodes[a["name"]] = {"type": a["type"],
                                         "labels": labels,
                                         "cloud": c}
            capa = int(reimu_config.youmu_jenkins["cfg_" + c]["capacity"])
            if capa == 0:
                capa = len(nodes)
            self.clouds[c] = {"capacity": capa,
                              "nodes": nodes}

        logger.info("Jenkins server check done.\n\n")

    def _new_server(self):
        self.server = jenkins.Jenkins(self._host, self._username, self._password)

    def _jenkins_folder_create(self):
        """
        All jobs in one folder
        """
        self._new_server()

        job_name = JenkinsServer.FOLDER_NAME

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

    def _jenkins_job_create(self, job_name: str, labels="", cmd="", artifacts=""):
        """
        Create job in folder
        """
        self._new_server()

        job_name = "{}/{}".format(JenkinsServer.FOLDER_NAME, job_name)

        if self.server.job_exists(job_name) and self.server.is_folder(job_name):
            logger.warn("Jenkins job {} exists but is a folder, delete it".format(job_name))
            self.server.delete_job(job_name)

        if not self.server.job_exists(job_name):
            logger.info("Create jenkins job {}".format(job_name))
            self.server.create_job(job_name, JenkinsServer._jenkins_job_gen_xml(labels, cmd, artifacts))
        else:
            logger.info("Reconfigure existing jenkins job {}".format(job_name))
            self.server.reconfig_job(job_name, JenkinsServer._jenkins_job_gen_xml(labels, cmd, artifacts))

    @staticmethod
    def _jenkins_job_gen_xml(labels: str, cmd: str, artifacts: str) -> str:
        et = ElementTree.fromstring(jenkins.EMPTY_CONFIG_XML)

        shell_ele = ElementTree.Element("hudson.tasks.Shell")
        cmd_ele = ElementTree.Element("command")
        cmd_ele.text = cmd
        shell_ele.append(cmd_ele)
        shell_ele.append(ElementTree.Element("configuredLocalRules"))

        builders_ele = ElementTree.Element("builders")
        builders_ele.append(shell_ele)

        archiver_ele = ElementTree.Element("hudson.tasks.ArtifactArchiver")
        artifacts_ele = ElementTree.Element("artifacts")
        artifacts_ele.text = artifacts
        archiver_ele.append(artifacts_ele)
        empty_archive_ele = ElementTree.Element("allowEmptyArchive")
        empty_archive_ele.text = "false"
        archiver_ele.append(empty_archive_ele)
        on_success_ele = ElementTree.Element("onlyIfSuccessful")
        on_success_ele.text = "true"
        archiver_ele.append(on_success_ele)
        fingerprint_ele = ElementTree.Element("fingerprint")
        fingerprint_ele.text = "false"
        archiver_ele.append(fingerprint_ele)
        ant_exclude_ele = ElementTree.Element("defaultExcludes")
        ant_exclude_ele.text = "true"
        archiver_ele.append(ant_exclude_ele)
        case_sensitive_ele = ElementTree.Element("caseSensitive")
        case_sensitive_ele.text = "true"
        archiver_ele.append(case_sensitive_ele)
        follow_symlinks_ele = ElementTree.Element("followSymlinks")
        follow_symlinks_ele.text = "true"
        archiver_ele.append(follow_symlinks_ele)

        publishers_ele = ElementTree.Element("publishers")
        publishers_ele.append(archiver_ele)

        node_ele = ElementTree.Element("assignedNode")
        node_ele.text = labels

        for e in et.findall("publishers"):
            et.remove(e)
        for e in et.findall("builders"):
            et.remove(e)
        for e in et.findall("assignedNode"):
            et.remove(e)
        et.append(builders_ele)
        et.append(publishers_ele)
        et.append(node_ele)

        return ElementTree.tostring(et).decode('utf-8')


youmu_jenkins = JenkinsServer()
