from utils.errors import AssertException


class ScriptGenerator:
    CMD_UPGRADE = {"debian": "{0} apt-get update && {0} apt-get upgrade -y",
                   "fedora": "{0} dnf upgrade -y",
                   "archlinux": "{0} pacman --noconfirm -Syuu",
                   "gentoo": "{0} emerge-webrsync"}
    CMD_MUGEN_DEP_INSTALL = {"debian": "{0} apt-get install -y sudo file expect git psmisc iputils-ping make"
                                       " python3-paramiko python3-six tar jq",
                             "fedora": "{0} dnf install -y sudo file expect git psmisc make iputils python3-six"
                                       " python3-paramiko tar jq",
                             "archlinux": "{0} pacman --need --noconfirm -S sudo file expect git psmisc make iputils"
                                          " python-six python-paramiko tar jq",
                             "gentoo": "{0} emerge --color=n --getbinpkg --noreplace --autounmask=y app-admin/sudo"
                                       " sys-apps/file dev-tcltk/expect dev-vcs/git sys-process/psmisc dev-build/make"
                                       " dev-python/paramiko dev-python/six app-arch/tar app-misc/jq"}

    def __init__(self, gen_type: str, distro_type: str, cfg: dict):
        self.distro_type = distro_type
        self.gen_type = gen_type
        self.cfg = cfg
        self.cmds = []
        # 默认为普通用户
        self.sudo = cfg.get("sudo", True)

        if gen_type == "mugen":
            self.test_platform = cfg["test_platform"]
            self._gen_upgrade_cmds()
            self._gen_mugen_test_cmds()
        elif gen_type == "upgrade":
            self._gen_upgrade_cmds()
        else:
            raise AssertException("Unknown command generate type {}".format(gen_type))

    def _gen_mugen_test_cmds(self):
        self._gen_upgrade_cmds()

        self.cmds.append(ScriptGenerator.CMD_MUGEN_DEP_INSTALL[self.distro_type])

        self.cmds.extend(["git clone --depth=1 https://gitee.com/ruyisdk/ruyi-mugen.git .",
                          "mkdir -p conf",
                          """echo '{{ "NODE": [{{ "ID": 1,
    "LOCALTION": "local",
    "MACHINE": "physical",
    "IPV6": "::1",
    "FRAME": "",
    "NIC": "",
    "MAC": "",
    "IPV4": "127.0.0.1",
    "USER": "",
    "PASSWORD": "",
    "SSH_PORT": 22,
    "BMC_IP": "",
    "BMC_USER": "",
    "BMC_PASSWORD": "" }}]}}' > conf/env.json""",
                          "bash ruyi_mugen.sh -f ruyi -x 2>&1 | tee report_gen_tmpl/26test_log.md",
                          "bash report_gen.sh {1}",
                          "{0} chown -R $USER:$USER ./* ./.*",
                          "rm -f *.md",
                          "mv ruyi-test-logs.tar.gz ruyi-test-{1}-logs.tar.gz",
                          "mv ruyi-test-logs_failed.tar.gz ruyi-test-{1}-logs_failed.tar.gz",
                          "mv ruyi_report/*.md ."])

    def _gen_upgrade_cmds(self):
        self.cmds.append(ScriptGenerator.CMD_UPGRADE[self.distro_type])

    def get_script(self) -> str:
        cmds = ""
        for c in self.cmds:
            cmds += c + "\n"
        return cmds.format("sudo" if self.sudo else "", self.test_platform)

    def get_artifacts(self) -> str:
        if self.gen_type != "mugen":
            raise AssertException("Only generate type mugen have artifacts")

        return "ruyi-test-{0}-logs.tar.gz, ruyi-test-{0}-logs_failed.tar.gz, *.md".format(self.test_platform)
