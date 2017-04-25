#!groovy

@Library('SovrinHelpers') _

def name = 'sovrinagent'

def testUbuntu = {
    try {
        echo 'Ubuntu Test: Checkout csm'
        checkout scm

        echo 'Ubuntu Test: Build docker image'
        def testEnv = dockerHelpers.build(name)

        testEnv.inside('--network host') {
            echo 'Ubuntu Test: Install dependencies'
            testHelpers.install()

            sh "pip install -r requirements.txt"
            sh "pip install pytest-html"

            echo 'Ubuntu Test: Test'
            sh "pytest --html=report.html --self-contained-html"
            //testHelpers.testJUnit(resFile: "test-result.${NODE_NAME}.xml")
        }
    }
    finally {
        echo 'Ubuntu Test: Cleanup'
        step([$class: 'WsCleanup'])
    }
}

def testWindows = {
    echo 'TODO: Implement me'
}

def testWindowsNoDocker = {
    echo 'TODO: Implement me'
}


testAndPublish(name, [ubuntu: testUbuntu])
