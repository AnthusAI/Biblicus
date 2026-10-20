Feature: GROBID runtime environment
  Biblicus reads its GROBID settings from Biblicus environment variables only.
  A caller that wraps Biblicus passes these names through; Biblicus never reads a caller's own names.

  Scenario: Biblicus environment variables configure the GROBID runtime
    Given the GROBID environment variable "BIBLICUS_GROBID_URL" is "http://grobid.example:9000/"
    And the GROBID environment variable "BIBLICUS_GROBID_CONTAINER_NAME" is "custom-grobid"
    And the GROBID environment variable "BIBLICUS_GROBID_DOCKER_IMAGE" is "example/grobid:1"
    Then the resolved GROBID base URL is "http://grobid.example:9000"
    And the resolved GROBID container name is "custom-grobid"
    And the resolved GROBID Docker image is "example/grobid:1"

  Scenario: Caller-specific GROBID environment variables are ignored
    Given the GROBID environment variable "BIBLICUS_GROBID_URL" is unset
    And the GROBID environment variable "BIBLICUS_GROBID_CONTAINER_NAME" is unset
    And the GROBID environment variable "BIBLICUS_GROBID_DOCKER_IMAGE" is unset
    And the GROBID environment variable "PAPYRUS_GROBID_URL" is "http://papyrus.example:9000"
    And the GROBID environment variable "PAPYRUS_GROBID_CONTAINER_NAME" is "papyrus-other"
    And the GROBID environment variable "PAPYRUS_GROBID_DOCKER_IMAGE" is "example/grobid:2"
    Then the resolved GROBID base URL is "http://127.0.0.1:8070"
    And the resolved GROBID container name is "biblicus-grobid"
    And the resolved GROBID Docker image is "grobid/grobid:0.9.1-crf"

  Scenario: The local GROBID container is published on localhost only with a restart policy and memory limits
    Given the GROBID environment variable "BIBLICUS_GROBID_CONTAINER_NAME" is unset
    And the GROBID environment variable "BIBLICUS_GROBID_DOCKER_IMAGE" is unset
    And the GROBID environment variable "BIBLICUS_GROBID_MEMORY_LIMIT" is unset
    Then the GROBID Docker run arguments for port 8070 are:
      | argument                  |
      | run                       |
      | -d                        |
      | --name                    |
      | biblicus-grobid           |
      | --restart                 |
      | unless-stopped            |
      | --memory                  |
      | 5g                        |
      | --memory-swap             |
      | 5g                        |
      | -e                        |
      | JAVA_OPTS=-Xms512m -Xmx2g |
      | -p                        |
      | 127.0.0.1:8070:8070       |
      | grobid/grobid:0.9.1-crf   |

  Scenario: The GROBID container memory limit is configurable
    Given the GROBID environment variable "BIBLICUS_GROBID_MEMORY_LIMIT" is "6g"
    Then the GROBID Docker run arguments contain the pair "--memory" "6g"
    And the GROBID Docker run arguments contain the pair "--memory-swap" "6g"

  Scenario: CrossRef consolidation is off by default for header and citations
    Given the GROBID environment variable "BIBLICUS_GROBID_CONSOLIDATE_HEADER" is unset
    And the GROBID environment variable "BIBLICUS_GROBID_CONSOLIDATE_CITATIONS" is unset
    Then the GROBID consolidation fields are header "0" and citations "0"

  Scenario: CrossRef header consolidation can be enabled on its own
    Given the GROBID environment variable "BIBLICUS_GROBID_CONSOLIDATE_HEADER" is "true"
    And the GROBID environment variable "BIBLICUS_GROBID_CONSOLIDATE_CITATIONS" is unset
    Then the GROBID consolidation fields are header "1" and citations "0"

  Scenario: CrossRef citation consolidation can be enabled on its own
    Given the GROBID environment variable "BIBLICUS_GROBID_CONSOLIDATE_HEADER" is unset
    And the GROBID environment variable "BIBLICUS_GROBID_CONSOLIDATE_CITATIONS" is "yes"
    Then the GROBID consolidation fields are header "0" and citations "1"
