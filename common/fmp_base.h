#include <stdint.h>
#ifdef __linux__
#define FASTMUSICPLAYER_EXPORT
#else
#define FASTMUSICPLAYER_EXPORT __declspec(dllexport)
#endif
#ifndef M_PI
#define M_PI 3.141592653589793238462643383279
#endif