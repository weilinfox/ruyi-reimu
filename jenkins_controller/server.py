import jenkins
import time
import xml.etree.ElementTree as ElementTree

from config.loader import reimu_config
from utils.errors import AssertException
from utils.github_operation import gh_op
from utils.logger import logger

from .script import ScriptGenerator


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
        # platforms reimu should test
        self.test_platforms = {}
        # platforms waiting in queue
        self.queued_platforms = []
        # job configured and build operation sent
        self.configured_platforms = []
        # testing
        self.testing_platforms = []
        self.testing_platforms_info = []
        self.testing_nodes = []
        # tested
        self.tested_platforms = []

        # reimu_config.reimu_status
        self.ruyi_version = ""
        self.ruyi_test_date = ""
        self.ruyi_testing = False

    def load(self):
        if not reimu_config.ready():
            raise Exception("ruyi-reimu not configured")

        jenkins_cfg = reimu_config.youmu_jenkins["jenkins"]
        self._host = jenkins_cfg["host"]
        self._username = jenkins_cfg["username"]
        self._password = jenkins_cfg["password"]

        # ruyi version
        self.ruyi_version = reimu_config.reimu_status["version"]
        self.ruyi_test_date = reimu_config.reimu_status["date"]
        self.ruyi_testing = reimu_config.reimu_status["testing"]

        # jenkins check
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
            # test platforms data
            self.test_platforms[p[0]] = {"labels": p[1]}

        for c in clouds:
            nodes = []
            for a in reimu_config.youmu_jenkins["agent_"+c]:
                labels = []
                nodes.append(a["name"])
                info = self.server.get_node_info(a["name"])
                for lb in info["assignedLabels"]:
                    labels.append(lb["name"])
                # nodes data
                self.nodes[a["name"]] = {"type": a["type"],
                                         "labels": labels,
                                         "cloud": c,
                                         "offline": info["offline"],
                                         "launchSupported": info["launchSupported"],
                                         "temporarilyOffline": info["temporarilyOffline"],
                                         "available": True,  # Will resign by _check(), available for reimu or not
                                         "testing": False}   # If this node in use by reimu
            capa = int(reimu_config.youmu_jenkins["cfg_" + c]["capacity"])
            if capa == 0:
                capa = len(nodes)
            # clouds data
            self.clouds[c] = {"capacity": capa,
                              "testing": 0,    # Now many nodes are in use by reimu
                              "nodes": nodes}  # Node list under this cloud

        logger.info("Jenkins server info load done.\n\n")

        self._check()

        # Restore status
        if self.ruyi_testing:
            ruyi_status = reimu_config.read_cache_status(self.ruyi_version)
            if not ruyi_status:
                self.ruyi_testing = False
            else:
                self.test_platforms = ruyi_status["test_platforms"]
                self.queued_platforms = ruyi_status["queued_platforms"]
                self.configured_platforms = ruyi_status["configured_platforms"]
                self.testing_platforms = ruyi_status["testing_platforms"]
                self.testing_platforms_info = ruyi_status["testing_platforms_info"]
                self.testing_nodes = ruyi_status["testing_nodes"]
                self.tested_platforms = ruyi_status["tested_platforms"]

                for c in ruyi_status["clouds_testing"].items():
                    self.clouds[c[0]]["testing"] = c[1]
                for n in ruyi_status["nodes_testing"].items():
                    self.nodes[n[0]]["testing"] = n[1]

        # New test
        if self.ruyi_testing:
            release = gh_op.get_repo_latest_release("ruyisdk/ruyi")
            tag = release.tag_name
            if self.ruyi_version != tag:
                self.ruyi_version = tag
                shanghai = time.gmtime(time.time()+28800)
                self.ruyi_test_date = "{}{}{}".format(shanghai.tm_year, shanghai.tm_mon, shanghai.tm_mday)

    def _status_store(self):
        reimu_config.reimu_status["version"] = self.ruyi_version
        reimu_config.reimu_status["date"] = self.ruyi_test_date
        reimu_config.reimu_status["testing"] = self.ruyi_testing

        clouds_testing = {}
        nodes_testing = {}
        for i in self.clouds.items():
            clouds_testing[i[0]] = i[1]["testing"]
        for i in self.nodes.items():
            nodes_testing[i[0]] = i[1]["testing"]
        reimu_config.cache_store({
            "test_platforms": self.test_platforms,
            "queued_platforms": self.queued_platforms,
            "configured_platforms": self.configured_platforms,
            "testing_platforms": self.testing_platforms,
            "testing_platforms_info": self.testing_platforms_info,
            "testing_nodes": self.testing_nodes,
            "tested_platforms": self.tested_platforms,
            "clouds_testing": clouds_testing,
            "nodes_testing": nodes_testing,
        })

    def test(self):
        self.ruyi_testing = True

        for p in self.test_platforms:
            self.queued_platforms.append(p)

        log_delay = 0
        retest_info = {}

        while self.queued_platforms or self.testing_platforms:
            # check testing queue
            end_queue = []
            end_status = []
            for i in range(0, len(self.testing_platforms)):
                end, info = self._jenkins_job_end(self.testing_platforms[i], self.testing_platforms_info[i]["number"])
                if end:
                    end_queue.append(i)
                    end_status.append(info["result"] == "SUCCESS")
                    logger.info('Platform {} test finished, status "{}"'
                                .format(self.testing_platforms[i], info["result"]))

            for i in range(0, len(end_queue)):
                if end_status[i]:
                    self.tested_platforms.append(self.testing_platforms[end_queue[i] - i])
                else:
                    # retest
                    if self.testing_platforms[end_queue[i] - i] in retest_info:
                        retest_info[self.testing_platforms[end_queue[i] - i]]["count"] += 1
                    else:
                        retest_info[self.testing_platforms[end_queue[i] - i]] = {"count": 1}
                    if retest_info[self.testing_platforms[end_queue[i] - i]]["count"] > 3:
                        retest_info[self.testing_platforms[end_queue[i] - i]]["count"] -= 1
                        logger.info('Platform {} test failed 3 times, will not retest'
                                    .format(self.testing_platforms[end_queue[i] - i]))
                    else:
                        self.queued_platforms.append(self.testing_platforms[end_queue[i] - i])
                        logger.info('Platform {} test failed, will retest'
                                    .format(self.testing_platforms[end_queue[i] - i]))

                self.nodes[self.testing_nodes[end_queue[i] - i]]["testing"] = False
                self.clouds[self.nodes[self.testing_nodes[end_queue[i] - i]]["cloud"]]["testing"] -= 1

                self.testing_nodes.pop(end_queue[i] - i)
                self.testing_platforms.pop(end_queue[i] - i)
                self.testing_platforms_info.pop(end_queue[i] - i)
            if self.testing_platforms and not end_queue and not log_delay:
                logger.info("No platform test finished")

            # find new platform to test
            wait_queue = []
            wait_node = []
            for p in self.queued_platforms:
                pl = self.test_platforms[p]["labels"]
                for n in self.nodes.items():
                    if not n[1]["available"]:
                        continue
                    if n[1]["testing"]:
                        continue
                    if self.clouds[n[1]["cloud"]]["capacity"] <= self.clouds[n[1]["cloud"]]["testing"]:
                        continue
                    flag = True
                    nl = n[1]["labels"]
                    for l in pl:
                        if l not in nl:
                            flag = False
                            break
                    if flag:
                        wait_queue.append(p)
                        wait_node.append(n[0])
                        n[1]["testing"] = True
                        self.clouds[n[1]["cloud"]]["testing"] += 1
                        break
            if self.queued_platforms and not wait_queue and not log_delay:
                logger.info("{} platforms stuck in queue".format(len(self.queued_platforms)))

            # configure job and send build operation
            for i in range(0, len(wait_queue)):
                script_gen = ScriptGenerator("mugen", self.nodes[wait_node[i]]["type"],
                                             {"sudo": True, "test_platform": wait_queue[i]})

                logger.info('Configure job for platform {}'.format(wait_queue[i]))

                self._jenkins_job_create(wait_queue[i], wait_node[i], script_gen.get_script(),
                                         script_gen.get_artifacts())
                bid = self._jenkins_job_build(wait_queue[i])

                self.configured_platforms.append((wait_queue[i], wait_node[i], bid))
                self.queued_platforms.remove(wait_queue[i])

            # check build started
            testing_queue = []
            for p in self.configured_platforms:
                info = self._jenkins_job_check_started(p[2])
                if info:
                    testing_queue.append((p, info))
            for t in testing_queue:
                self.configured_platforms.remove(t[0])
                self.testing_platforms.append(t[0][0])
                self.testing_nodes.append(t[0][1])
                self.testing_platforms_info.append(t[1])
                logger.info('Platform {} is testing, check url {}'.format(t[0][0], t[1]["url"]))

            # sleep 10s
            sleep_time = 10
            time.sleep(sleep_time)
            log_delay -= 1
            if log_delay < 0:
                # 15m
                log_delay = int(15 * 60 / sleep_time)

        self.ruyi_testing = False
        logger.info("Jenkins test done.\n\n")

    def _check(self):
        nodes = self.server.get_nodes()
        for n in nodes:
            if n["name"] in self.nodes:
                continue
            logger.warn("Node \"{}\"({}) exists but not available in this configuration"
                        .format(n["name"], "offline" if n["offline"] else "online"))

        for n in self.nodes.items():
            if n[1]["offline"] and not n[1]["launchSupported"]:
                logger.warn("Node \"{}\" is offline but cannot be automatically launched".format(n[0]))
                n[1]["available"] = False
            if n[1]["temporarilyOffline"]:
                logger.warn("Node \"{}\"({}) was temporarily marked offline and unavaiable"
                            .format(n[0], "offline" if n[1]["offline"] else "online"))
                n[1]["available"] = False

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

    def _jenkins_job_create(self, job_name: str, labels: str, cmd: str, artifacts: str):
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

    def _jenkins_job_build(self, job_name: str) -> int:
        self._new_server()

        job_name = "{}/{}".format(JenkinsServer.FOLDER_NAME, job_name)
        return self.server.build_job(job_name)

    def _jenkins_job_check_started(self, bid: int) -> dict:
        self._new_server()

        info = self.server.get_queue_item(bid)
        if (info and "executable" in info
                and info["executable"] and "number" in info["executable"] and "url" in info["executable"]):
            return {"number": info["executable"]["number"], "url": info["executable"]["url"]}
        return {}

    def _jenkins_job_end(self, job_name: str, number: int) -> (bool, dict):
        self._new_server()

        job_name = "{}/{}".format(JenkinsServer.FOLDER_NAME, job_name)

        info = self.server.get_build_info(job_name, number)

        if info["inProgress"]:
            return False, {}

        return True, {"inProgress": info["inProgress"], "result": info["result"]}

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
        roam_ele = ElementTree.Element("canRoam")
        roam_ele.text = "false"

        for e in et.findall("publishers"):
            et.remove(e)
        for e in et.findall("builders"):
            et.remove(e)
        for e in et.findall("assignedNode"):
            et.remove(e)
        for e in et.findall("canRoam"):
            et.remove(e)
        et.append(builders_ele)
        et.append(publishers_ele)
        et.append(node_ele)
        et.append(roam_ele)

        return ElementTree.tostring(et).decode('utf-8')


youmu_jenkins = JenkinsServer()
