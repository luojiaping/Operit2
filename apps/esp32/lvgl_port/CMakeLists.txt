idf_component_register(
    SRCS "operit_lvgl.c" "layout_store.c"
    INCLUDE_DIRS "."
    REQUIRES lvgl__lvgl esp_timer esp_partition spi_flash
)
