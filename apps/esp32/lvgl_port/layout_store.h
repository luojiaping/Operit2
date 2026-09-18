#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
typedef struct {
    uint8_t type,parent; uint16_t x,y,w,h; uint32_t color;
    uint8_t radius,value,font;
    const char *text,*action,*hold,*binding;
} operit_packed_node_t;
typedef struct { char id[24],left[24],right[24]; uint32_t color; uint8_t count; const uint8_t *nodes; } operit_packed_page_t;
void operit_store_init(void);
bool operit_store_poll(void);
const char *operit_store_entry(void);
bool operit_store_page(const char *id, operit_packed_page_t *page);
const uint8_t *operit_store_node(const uint8_t *data,operit_packed_node_t *node,char *strings);
int operit_store_begin(size_t length);
int operit_store_write(const uint8_t *data,size_t length);
int operit_store_finish(void);
void operit_store_abort(void);
unsigned operit_store_revision(void);
bool operit_store_validate(const uint8_t *data,size_t length);
