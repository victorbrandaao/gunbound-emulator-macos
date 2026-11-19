/* Inicializador do cliente privado. Formato de login: jglim/gunbound-launcher (MIT). */
#include <windows.h>
#include <bcrypt.h>
#include <stdio.h>
#include <string.h>
#include <conio.h>

static int credentials(char *out) {
    char user[80]={0},pass[80]={0}; int n=0,ch;
    printf("GunBound Season 2 - grupo privado\nUsuario: ");
    if(!fgets(user,sizeof(user),stdin)) return 0;
    user[strcspn(user,"\r\n")]=0;
    printf("Senha: ");
    while((ch=_getch())!='\r' && ch!='\n') {
        if(ch==3||ch==27)return 0;
        if(ch==8){if(n)n--;continue;}
        if(ch>=33&&ch<127&&n<79)pass[n++]=(char)ch;
    }
    printf("\n");
    if(!strlen(user)||strlen(user)>16||!n||n>16){printf("Usuario/senha: maximo de 16 caracteres.\n");return 0;}
    BYTE plain[48]={0},encrypted[48],key[]={0xFA,0xEE,0x85,0xF2,0x40,0x73,0xD9,0x16,0x13,0x90,0x19,0x7F,0x6E,0x56,0x2A,0x67};
    memcpy(plain,user,strlen(user));memcpy(plain+16,pass,n);
    BCRYPT_ALG_HANDLE alg=0;BCRYPT_KEY_HANDLE aes=0;DWORD size=0,objlen=0;PUCHAR obj=0;int ok=0;
    if(BCryptOpenAlgorithmProvider(&alg,BCRYPT_AES_ALGORITHM,0,0)<0)goto done;
    if(BCryptSetProperty(alg,BCRYPT_CHAINING_MODE,(PUCHAR)BCRYPT_CHAIN_MODE_ECB,sizeof(BCRYPT_CHAIN_MODE_ECB),0)<0)goto done;
    if(BCryptGetProperty(alg,BCRYPT_OBJECT_LENGTH,(PUCHAR)&objlen,sizeof(objlen),&size,0)<0)goto done;
    obj=HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,objlen);
    if(!obj||BCryptGenerateSymmetricKey(alg,&aes,obj,objlen,key,sizeof(key),0)<0)goto done;
    if(BCryptEncrypt(aes,plain,sizeof(plain),0,0,0,encrypted,sizeof(encrypted),&size,0)<0||size!=48)goto done;
    for(n=0;n<48;n++)sprintf(out+n*2,"%02X",encrypted[n]);ok=1;
 done:
    SecureZeroMemory(pass,sizeof(pass));SecureZeroMemory(plain,sizeof(plain));
    if(aes)BCryptDestroyKey(aes);if(obj)HeapFree(GetProcessHeap(),0,obj);if(alg)BCryptCloseAlgorithmProvider(alg,0);
    return ok;
}
int main(int argc,char **argv) {
    char directory[MAX_PATH],game[MAX_PATH],ini[MAX_PATH],ip[64],buddy[64],cmd[1024]={0};
    GetModuleFileNameA(0,directory,sizeof(directory));char *end=strrchr(directory,'\\');if(!end)return 2;*end=0;
    SetCurrentDirectoryA(directory);snprintf(game,sizeof(game),"%s\\GunBound.gme",directory);
    snprintf(ini,sizeof(ini),"%s\\GunBound.ini",directory);
    GetPrivateProfileStringA("Gunbound","BrokerServerIP","127.0.0.1",ip,sizeof(ip),ini);
    GetPrivateProfileStringA("Gunbound","BuddyIP",ip,buddy,sizeof(buddy),ini);
    DWORD port=GetPrivateProfileIntA("Gunbound","BrokerServerPort",8372,ini),version=4;
    const char *keys[]={"Software\\Softnyx\\GunBoundWC","Software\\Softnyx\\GunBound"};
    HKEY roots[]={HKEY_CURRENT_USER,HKEY_LOCAL_MACHINE};
    for(int r=0;r<2;r++)for(int i=0;i<2;i++){HKEY k;
        if(RegCreateKeyExA(roots[r],keys[i],0,0,0,KEY_WRITE|KEY_WOW64_32KEY,0,&k,0)==0){
            RegSetValueExA(k,"IP",0,REG_SZ,(BYTE*)ip,strlen(ip)+1);
            RegSetValueExA(k,"BuddyIP",0,REG_SZ,(BYTE*)buddy,strlen(buddy)+1);
            RegSetValueExA(k,"Location",0,REG_SZ,(BYTE*)directory,strlen(directory)+1);
            RegSetValueExA(k,"Version",0,REG_DWORD,(BYTE*)&version,4);
            RegSetValueExA(k,"Port",0,REG_DWORD,(BYTE*)&port,4);RegCloseKey(k);
        }
    }
    if(argc==2){if(strlen(argv[1])!=96)return 2;strcpy(cmd,argv[1]);}
    else if(!credentials(cmd)){printf("Nao foi possivel preparar o login.\n");return 2;}
    STARTUPINFOA si={0};PROCESS_INFORMATION pi={0};si.cb=sizeof(si);
    if(!CreateProcessA(game,cmd,0,0,FALSE,0,0,directory,&si,&pi)){
        printf("Nao foi possivel abrir o jogo. Erro %lu\n",GetLastError());getchar();return 3;}
    ShowWindow(GetConsoleWindow(),SW_MINIMIZE);
    WaitForSingleObject(pi.hProcess,INFINITE);DWORD result;GetExitCodeProcess(pi.hProcess,&result);
    CloseHandle(pi.hProcess);CloseHandle(pi.hThread);return (int)result;
}
