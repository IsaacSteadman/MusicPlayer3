#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

BOOL WINAPI DllMain(
  _In_ HINSTANCE hinstDLL,
  _In_ DWORD     fdwReason,
  _In_ LPVOID    lpvReserved
){
	return TRUE;
}