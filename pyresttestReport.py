# -*- coding: utf-8 -*-

import time
import os
import sys
import argparse
import yaml
from subprocess import Popen, PIPE
from lib.htmlReport import HTMLReport


def getParse(args):
    """解析各种文件路径参数"""
    parser = argparse.ArgumentParser(description='pyresttest report')
    parser.add_argument("-url", action="store", dest="test_url", default="", type=str)
    parser.add_argument("-out", action="store", dest="output_file_path", default="", type=str)
    parser.add_argument("-test", action="store", nargs="+", dest="test_file_path", default="", type=str)
    return parser.parse_args(args)


def getTestInfo(test_file_path):
    """从yaml里取出test case的相关信息,目前只要名字"""
    yl = yaml.load(open(test_file_path, "rb"))
    caseNames = []
    for block in yl:
        if "test" not in block:
            continue
        caseName = "no name case"
        for elem in block["test"]:
            if "name" in elem:
                caseName = elem["name"]
                break
        caseNames.append(caseName)
    return caseNames


def resttest(tests=None, url="", out=""):
    """跑pyresttest,并输出测试文件"""
    if not tests:
        raise Exception("need at least one test file path, like: path/xxx.yaml")
    finalTests = []
    for case in tests:
        if os.path.split(case)[-1].split(".")[-1] != "yaml":
            # 加入目录下的所有yaml作为测试用例
            for root, dirs, files in os.walk(case):
                for name in files:
                    if name.split(".")[-1] == "yaml":
                        finalTests.append(os.path.join(root, name))
        else:
            finalTests.append(case)
    if not url:
        raise Exception("need url, like: https://www.baidu.com")
    app = "pyresttest"
    outFile = out if out else "./default_output.html"

    startTime = time.time()
    startTimeStr = time.strftime('%Y-%m-%d %H:%M:%S')

    results = {}

    no = 0
    for case in finalTests:
        no += 1
        caseNames = getTestInfo(case)
        casePtr = 0
        # print "cmd: %s %s %s" % (app, url, case)

        proc = Popen([app, url, case], stdout=PIPE, stderr=PIPE)
        out = proc.communicate()

        err = out[1].split("\n")  # err 取出来

        # print ">>>>>\n", out[1], "\n\n"

        results[case] = []
        errSize = len(err)
        no = 0
        while no < errSize:
            if err[no] == "" or err[no].find("ERROR:Test Failed: ") == -1:
                no += 1
                continue
            case_name = err[no][len("ERROR:Test Failed: "): err[no].find(" URL=")]
            reson = err[no + 1][len("ERROR:Test Failure, failure type: "):]
            while casePtr < len(caseNames) and caseNames[casePtr] != case_name:
                results[case].append((caseNames[casePtr], "passed", ""))
                casePtr += 1
            results[case].append((case_name, "failed", reson))
            casePtr += 1
            no += 1

        while casePtr < len(caseNames):
            results[case].append((caseNames[casePtr], "passed", ""))
            casePtr += 1

    duration = time.time() - startTime

    htmlResult = {"passed": 0, "failed": 0, "error": 0, "result": {}, "startTime": startTimeStr, "duration": str(duration) + "(s)"}
    for key in results:
        print ">>>>> test file:", key, "<<<<<<"
        total = 0
        passed = 0
        caseResult = {"np": 0, "nf": 0, "ne": 0, "desc": key, "details": []}
        caseID = len(htmlResult["result"])
        for line in results[key]:
            print line
            if line[1] == "passed":
                passed += 1
                htmlResult["passed"] += 1
                caseResult["np"] += 1
                caseResult["details"].append((0, line[0], "", ""))
            elif line[1] == "failed":
                htmlResult["failed"] += 1
                caseResult["nf"] += 1
                caseResult["details"].append((1, line[0], line[2], ""))
            total += 1
        print "result: {0}/{1} passed\n".format(passed, total)
        htmlResult["result"][caseID] = caseResult

    fp = open(outFile, "wb")
    HTMLReport(stream=fp, title="Pyresttest Report").generateReport(htmlResult)

if __name__ == "__main__":
    kwargs = getParse(sys.argv[1:])
    resttest(kwargs.test_file_path, kwargs.test_url, kwargs.output_file_path)
