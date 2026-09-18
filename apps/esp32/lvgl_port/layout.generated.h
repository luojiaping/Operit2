/* Generated from apps/esp32/ui/layout.json; edit JSON, not this file. */
#define OPERIT_LAYOUT_ENABLED 1
#define OPERIT_LAYOUT_ENTRY "home"
static const operit_layout_node_t layout_page_0[] = {
 {1,-1,182,172,118,24,0x53dfc5,0,0,"OPERIT / EDGE","","","",14},
 {1,-1,226,20,74,24,0xf4f8ff,0,0,"Aurora","","","",14},
 {0,-1,18,48,284,111,0x172a3d,22,0,"","","","",14},
 {1,-1,31,56,262,58,0xf4f8ff,0,0,"00:00","","","clock",48},
 {1,-1,73,119,230,24,0xf4f8ff,0,0,"DEVICE TIME / UPTIME","","","",14},
 {1,-1,16,21,272,24,0x53dfc5,0,0,"WIFI STARTING","","","connection",14},
 {2,-1,20,173,124,28,0x216c73,12,0,"Apps >","go:apps","","",14}
};
static const operit_layout_node_t layout_page_1[] = {
 {2,-1,12,10,36,32,0x216c73,12,0,"<","go:home","","",14},
 {1,-1,58,16,246,24,0xf4f8ff,0,0,"APPS","","","",14},
 {2,-1,24,48,56,56,0x216c73,12,0,"Face","go:face","","",14},
 {1,-1,22,106,86,22,0xf4f8ff,0,0,"Face","","","",14},
 {2,-1,124,48,56,56,0x216c73,12,0,"Plugins","go:plugins","","",14},
 {1,-1,122,106,86,22,0xf4f8ff,0,0,"Plugins","","","",14},
 {2,-1,224,48,56,56,0x216c73,12,0,"Theme","go:theme","","",14},
 {1,-1,222,106,86,22,0xf4f8ff,0,0,"Theme","","","",14},
 {2,-1,24,136,56,56,0x216c73,12,0,"Settings","go:settings","","",14},
 {1,-1,22,194,86,22,0xf4f8ff,0,0,"Settings","","","",14},
 {2,-1,124,136,56,56,0x216c73,12,0,"Terminal","go:terminal","","",14},
 {1,-1,122,194,86,22,0xf4f8ff,0,0,"Terminal","","","",14},
 {2,-1,224,136,56,56,0x216c73,12,0,"Network","go:network","","",14},
 {1,-1,222,194,86,22,0xf4f8ff,0,0,"Network","","","",14}
};
static const operit_layout_node_t layout_page_2[] = {
 {2,-1,12,10,36,32,0x216c73,12,0,"<","go:apps","","",14},
 {1,-1,58,16,246,24,0xf4f8ff,0,0,"THEME","","","",14},
 {1,-1,20,58,280,24,0xf4f8ff,0,0,"COLOR PALETTE","","","",14},
 {2,-1,20,88,280,42,0x216c73,12,0,"Next palette","theme_next","","",14},
 {2,-1,20,172,280,42,0x216c73,12,0,"Icon shape","shape_toggle","","",14}
};
static const operit_layout_node_t layout_page_3[] = {
 {2,-1,12,10,36,32,0x216c73,12,0,"<","go:apps","","",14},
 {1,-1,58,16,246,24,0xf4f8ff,0,0,"SETTINGS","","","",14},
 {1,-1,20,66,280,26,0xf4f8ff,0,0,"Wi-Fi status","","","connection",14},
 {1,-1,20,114,280,24,0xf4f8ff,0,0,"Display 320 x 240","","","",14},
 {2,-1,20,180,280,40,0x216c73,12,0,"Appearance","go:theme","","",14}
};
static const operit_layout_node_t layout_page_4[] = {
 {2,-1,12,10,36,32,0x216c73,12,0,"<","go:apps","","",14},
 {1,-1,58,16,246,24,0xf4f8ff,0,0,"NETWORK","","","",14},
 {1,-1,20,66,280,26,0xf4f8ff,0,0,"Wi-Fi status","","","connection",14},
 {1,-1,20,120,280,40,0xf4f8ff,0,0,"Configure Wi-Fi on device web","","","",14}
};
static const operit_layout_node_t layout_page_5[] = {
 {2,-1,12,10,36,32,0x216c73,12,0,"<","go:apps","","",14},
 {1,-1,58,16,246,24,0xf4f8ff,0,0,"FACE","","","",14},
 {1,-1,50,65,220,58,0x53dfc5,0,0,"o   o","","","",48},
 {1,-1,80,136,160,24,0xf4f8ff,0,0,"neutral","","","expression",14},
 {2,-1,90,180,140,40,0x216c73,12,0,"Online","face_online","","",14}
};
static const operit_layout_node_t layout_page_6[] = {
 {2,-1,12,10,36,32,0x216c73,12,0,"<","go:apps","","",14},
 {1,-1,58,16,246,24,0xf4f8ff,0,0,"TERMINAL","","","",14},
 {1,-1,20,70,280,24,0x53dfc5,0,0,"> Operit Edge ready","","","",14},
 {1,-1,20,106,280,24,0xf4f8ff,0,0,"Local display + Wi-Fi","","","",14},
 {2,-1,20,180,280,40,0x216c73,12,0,"Run node","run_node","","",14}
};
static const operit_layout_node_t layout_page_7[] = {
 {2,-1,12,10,36,32,0x216c73,12,0,"<","go:apps","","",14},
 {1,-1,58,16,246,24,0xf4f8ff,0,0,"PLUGINS","","","",14},
 {1,-1,20,92,280,32,0xf4f8ff,0,0,"No plugins installed","","","",14}
};
static const operit_layout_page_t layout_pages[] = {
 {"home",0x091420,layout_page_0,7,"apps",""},
 {"apps",0x091420,layout_page_1,14,"","home"},
 {"theme",0x091420,layout_page_2,5,"",""},
 {"settings",0x091420,layout_page_3,5,"",""},
 {"network",0x091420,layout_page_4,4,"",""},
 {"face",0x091420,layout_page_5,5,"",""},
 {"terminal",0x091420,layout_page_6,5,"",""},
 {"plugins",0x091420,layout_page_7,3,"",""}
};
#define OPERIT_PAGE_COUNT 8
