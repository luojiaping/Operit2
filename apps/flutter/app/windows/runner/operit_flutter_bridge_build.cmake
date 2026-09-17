# Builds and copies the Rust artifacts required by the selected Windows runner configuration.
file(MAKE_DIRECTORY "${OPERIT_OUTPUT_DIRECTORY}")

# rustup's cargo.exe is a proxy. MSBuild often omits RUSTUP_HOME, so derive it.
get_filename_component(OPERIT_CARGO_ABSOLUTE "${OPERIT_CARGO_EXECUTABLE}" ABSOLUTE)
get_filename_component(OPERIT_CARGO_BIN_DIR "${OPERIT_CARGO_ABSOLUTE}" DIRECTORY)
if(EXISTS "${OPERIT_CARGO_BIN_DIR}/rustup.exe" OR EXISTS "${OPERIT_CARGO_BIN_DIR}/rustup")
  get_filename_component(OPERIT_CARGO_HOME_DIR "${OPERIT_CARGO_BIN_DIR}" DIRECTORY)
  get_filename_component(OPERIT_TOOLCHAIN_ROOT "${OPERIT_CARGO_HOME_DIR}" DIRECTORY)
  if(NOT DEFINED ENV{CARGO_HOME} OR "$ENV{CARGO_HOME}" STREQUAL "")
    set(ENV{CARGO_HOME} "${OPERIT_CARGO_HOME_DIR}")
  endif()
  if(EXISTS "${OPERIT_TOOLCHAIN_ROOT}/rustup")
    if(NOT DEFINED ENV{RUSTUP_HOME} OR "$ENV{RUSTUP_HOME}" STREQUAL "")
      set(ENV{RUSTUP_HOME} "${OPERIT_TOOLCHAIN_ROOT}/rustup")
    endif()
  elseif(EXISTS "${OPERIT_TOOLCHAIN_ROOT}/.rustup")
    if(NOT DEFINED ENV{RUSTUP_HOME} OR "$ENV{RUSTUP_HOME}" STREQUAL "")
      set(ENV{RUSTUP_HOME} "${OPERIT_TOOLCHAIN_ROOT}/.rustup")
    endif()
  endif()
endif()

if(OPERIT_BUILD_CONFIG STREQUAL "Debug")
  execute_process(
    COMMAND "${CMAKE_COMMAND}" -E env
      "RUSTFLAGS=-Awarnings"
      "CARGO_TERM_COLOR=never"
      "${OPERIT_CARGO_EXECUTABLE}" build --quiet --manifest-path "${OPERIT_FLUTTER_BRIDGE_CRATE}/Cargo.toml"
    WORKING_DIRECTORY "${OPERIT_FLUTTER_BRIDGE_CRATE}"
    RESULT_VARIABLE OPERIT_CARGO_RESULT
  )
  if(NOT OPERIT_CARGO_RESULT EQUAL 0)
    message(FATAL_ERROR "operit flutter bridge Debug build failed: ${OPERIT_CARGO_RESULT}")
  endif()
  file(COPY_FILE
    "${OPERIT_FLUTTER_BRIDGE_CRATE}/target/debug/operit_flutter_bridge.dll"
    "${OPERIT_OUTPUT_DIRECTORY}/operit_flutter_bridge.dll"
    ONLY_IF_DIFFERENT
  )
else()
  execute_process(
    COMMAND "${CMAKE_COMMAND}" -E env
      "RUSTFLAGS=-Awarnings"
      "CARGO_TERM_COLOR=never"
      "${OPERIT_CARGO_EXECUTABLE}" build --quiet --manifest-path "${OPERIT_FLUTTER_BRIDGE_CRATE}/Cargo.toml" --release
    WORKING_DIRECTORY "${OPERIT_FLUTTER_BRIDGE_CRATE}"
    RESULT_VARIABLE OPERIT_CARGO_RESULT
  )
  if(NOT OPERIT_CARGO_RESULT EQUAL 0)
    message(FATAL_ERROR "operit flutter bridge release build failed: ${OPERIT_CARGO_RESULT}")
  endif()
  file(COPY_FILE
    "${OPERIT_FLUTTER_BRIDGE_CRATE}/target/release/operit_flutter_bridge.dll"
    "${OPERIT_OUTPUT_DIRECTORY}/operit_flutter_bridge.dll"
    ONLY_IF_DIFFERENT
  )
endif()
