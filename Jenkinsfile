pipeline {
    agent {
        kubernetes {
        yaml '''
apiVersion: v1
kind: Pod
spec:
    containers:
        -
            name: argo
            image: 'docker.generalmills.com/k8s-argocli:stable'
            command:
                - cat
            tty: true
        -
            name: python
            image: 'python:3.6'
            command:
                - cat
            tty: true
'''
        }
    }
    environment {
        PROJECT_NAME = 'ea-production-scheduling-optimization'
        IMAGE_REGISTRY = 'docker.generalmills.com'
        GIT_COMMIT_SHORT = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
    }

    stages {
        stage('Setup') {
            steps {
                beginBuild()
                updatePullRequestStatus state: 'pending'
            }
        }


        stage('Test & Analysis') {
            steps {
                container('python') {
                    sh 'pip install --no-cache-dir pylint black'
                    sh 'black --check src/$PROJECT_NAME/'
                }
            }
        }
        
        stage('Build') {
            agent { label 'linux' }
            steps {
                sh 'docker build . -t $IMAGE_REGISTRY/docker-snapshot-local/$PROJECT_NAME:$BUILD_NUMBER-$GIT_COMMIT_SHORT'
                pushToArtifactoryContainerImage image: "$PROJECT_NAME", tag: "$BUILD_NUMBER-$GIT_COMMIT_SHORT", registry: "$IMAGE_REGISTRY"
                scanBuild buildName: "$PROJECT_NAME", buildNumber: "$BUILD_NUMBER-$GIT_COMMIT_SHORT"
            }
        }

        stage('Deploy Development') {
            when { not { branch 'main' } }
            steps {
                container('argo') {
                    // You can add one more attribute app_env: 'dev' below in case of an environment based deployment eg: deployK8sApplicationV2 cluster_env: 'nonprod', app_env: 'dev', extra_args: """
                    deployK8sApplicationV2 cluster_env: 'nonprod', extra_args: """
                        helm:
                            releaseName: "${PROJECT_NAME}"
                            values:
                                image:
                                    "repository": "${IMAGE_REGISTRY}/${PROJECT_NAME}"
                                    "tag": "${BUILD_NUMBER}-${GIT_COMMIT_SHORT}"
                                istio:
                                    hosts:
                                    - "${PROJECT_NAME}-${BRANCH_NAME.toLowerCase().replaceAll(/[^a-z0-9-]+/,'-')}.k8s.genmills.com"
                                    # if app needs to be exposed externally change the value of type to external for that specific environment. default is internal.
                                    # type: internal
                                # Example: Uncomment to add extra environment variables
                                # extraEnvs:
                                #     MY_ENV_VARIABLE: myvariable
                                #     My_BRANCH: ${BRANCH_NAME}
                                #     MY_POD_IP:
                                #          valueFrom:
                                #              fieldRef:
                                #                  fieldPath: status.podIP
                    """
                }
            }
        }

        stage('Deploy Production') {
            when { branch 'main' }
            steps {
                promoteContainerImage image: "$PROJECT_NAME", tag: "$BUILD_NUMBER-$GIT_COMMIT_SHORT"
                container('argo') {
                    // You can add one more attribute app_env: 'prod' below in case of an environment based deployment eg: deployK8sApplicationV2 cluster_env: 'prod', app_env: 'prod', extra_args: """
                    deployK8sApplicationV2 cluster_env: 'prod', extra_args: """
                        helm:
                            releaseName: "${PROJECT_NAME}"
                            values:
                                image:
                                    "repository": "${IMAGE_REGISTRY}/${PROJECT_NAME}"
                                    "tag": "${BUILD_NUMBER}-${GIT_COMMIT_SHORT}"
                                istio:
                                    hosts:
                                    - "${PROJECT_NAME}.k8s.genmills.com"
                                    # if app needs to be exposed externally change the value of type to external for that specific environment. default is internal.
                                    # type: internal
                                autoscaling:
                                    enabled: true
                                # Example: Uncomment to add extra environment variables
                                # extraEnvs:
                                #     MY_ENV_VARIABLE: myvariable
                                #     My_BRANCH: ${BRANCH_NAME}
                                #     MY_POD_IP:
                                #          valueFrom:
                                #              fieldRef:
                                #                  fieldPath: status.podIP
                    """
                }
            }
        }
    }

    post {
        always {
            postBuild()
        }
        success {
            updatePullRequestStatus state: 'succeeded'
        }
        failure {
            updatePullRequestStatus state: 'failed'
        }
    }
}
