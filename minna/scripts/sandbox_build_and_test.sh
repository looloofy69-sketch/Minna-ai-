#!/usr/bin/env bash
# Offline build + JUnit run for a plain Kotlin/JVM source tree, using only jars that ship inside a Gradle
# distribution already on the machine. Intended for sandboxes where Maven Central is unreachable; on a
# normal machine or CI use `gradle test` instead.
#
# usage: sandbox_build_and_test.sh <project_dir>   (expects <dir>/src/main/kotlin and <dir>/src/test/kotlin)
# env:   GRADLE_LIB  directory holding the Gradle distribution jars (default /opt/gradle/lib)
# output: one machine-readable line:  RESULT main_errors=N test_errors=N run=<JUnit summary>
# Writes build output and logs to <project_dir>/out (git-ignored).
set -uo pipefail
P=${1:?project dir}
G=${GRADLE_LIB:-/opt/gradle/lib}
STD=$(ls "$G"/kotlin-stdlib-2.*.jar | head -1)
ANN=$(ls "$G"/annotations-*.jar | head -1)
JU="$(ls "$G"/junit-4.*.jar | head -1):$(ls "$G"/hamcrest-core-*.jar | head -1)"
KC="$(ls "$G"/kotlin-compiler-embeddable-*.jar | head -1):$STD:$ANN:$(ls "$G"/kotlin-reflect-*.jar | head -1):$(ls "$G"/kotlin-script-runtime-*.jar | head -1):$(ls "$G"/kotlin-daemon-embeddable-*.jar | head -1):$(ls "$G"/trove4j-*.jar | head -1):$(ls "$G"/kotlinx-coroutines-core-jvm-*.jar | head -1)"
kc() { java -cp "$KC" org.jetbrains.kotlin.cli.jvm.K2JVMCompiler -no-stdlib -no-reflect -jvm-target 17 "$@" 2>&1 | grep -v '^Picked up'; }

rm -rf "$P/out"; mkdir -p "$P/out/main" "$P/out/test"

kc -cp "$STD:$ANN" -d "$P/out/main" $(find "$P/src/main" -name '*.kt') > "$P/out/main.log"
main_errors=$(grep -cE '(: error:|^exception:)' "$P/out/main.log")

kc -cp "$P/out/main:$STD:$ANN:$JU" -d "$P/out/test" $(find "$P/src/test" -name '*.kt') > "$P/out/test.log"
test_errors=$(grep -cE '(: error:|^exception:)' "$P/out/test.log")

CLASSES=$(cd "$P/out/test" && find . -name '*Test.class' | sed 's|^\./||; s|\.class$||; s|/|.|g' | sort | tr '\n' ' ')
java -cp "$P/out/main:$P/out/test:$STD:$ANN:$JU" org.junit.runner.JUnitCore $CLASSES 2>&1 | grep -v '^Picked up' > "$P/out/run.log"
summary=$(grep -E '^(OK \(|Tests run:)' "$P/out/run.log" | tr '\n' ' ')
echo "RESULT main_errors=$main_errors test_errors=$test_errors run=${summary:-NO_RUN_OUTPUT}"
