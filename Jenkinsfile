// Declarative pipeline for the daily lead-gen run.
//
// Prerequisites on the Jenkins host:
//   * Docker available to Jenkins (mount the host docker socket into the
//     Jenkins container, or run Jenkins on a host with Docker).
//   * Credentials configured in Jenkins (Manage Jenkins -> Credentials):
//       - apify-token        (Secret text)
//       - supabase-url       (Secret text)
//       - supabase-key       (Secret text)
//       - groq-api-key       (Secret text)
//       - google-sheet-id    (Secret text)
//       - google-sa-json     (Secret file -> the service-account JSON)
//
// The job builds the pipeline image and runs main.py inside it once per day.

pipeline {
    agent any

    triggers {
        // Daily at ~07:00. 'H' jitters the minute to spread load.
        cron('H 7 * * *')
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    environment {
        IMAGE = "leadgen:${env.BUILD_NUMBER}"
    }

    stages {
        stage('Build image') {
            steps {
                sh 'docker build -t $IMAGE .'
            }
        }

        stage('Run pipeline') {
            steps {
                withCredentials([
                    string(credentialsId: 'apify-token',     variable: 'APIFY_TOKEN'),
                    string(credentialsId: 'supabase-url',     variable: 'SUPABASE_URL'),
                    string(credentialsId: 'supabase-key',     variable: 'SUPABASE_KEY'),
                    string(credentialsId: 'groq-api-key',     variable: 'GROQ_API_KEY'),
                    string(credentialsId: 'google-sheet-id',  variable: 'GOOGLE_SHEET_ID'),
                    file(credentialsId:   'google-sa-json',   variable: 'GOOGLE_SA_FILE')
                ]) {
                    sh '''
                        mkdir -p "$WORKSPACE/output"
                        docker run --rm \
                          -e APIFY_TOKEN \
                          -e SUPABASE_URL \
                          -e SUPABASE_KEY \
                          -e GROQ_API_KEY \
                          -e GOOGLE_SHEET_ID \
                          -e GOOGLE_SERVICE_ACCOUNT_JSON=/run/google-sa.json \
                          -v "$GOOGLE_SA_FILE":/run/google-sa.json:ro \
                          -v "$WORKSPACE/output":/app/output \
                          $IMAGE
                    '''
                }
            }
        }
    }

    post {
        success {
            archiveArtifacts artifacts: 'output/*.csv', allowEmptyArchive: true, fingerprint: true
        }
        cleanup {
            sh 'docker rmi $IMAGE || true'
        }
    }
}
