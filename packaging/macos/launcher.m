#import <Foundation/Foundation.h>
#import <AppKit/AppKit.h>
#include <unistd.h>

/* Keep the original executable/module contract; the native launcher only
 * resolves relocatable resources and writable per-user state, then execs it. */
int main(int argc, char **argv) {
    @autoreleasepool {
        NSBundle *bundle = NSBundle.mainBundle;
        NSString *resources = bundle.resourcePath;
        NSString *support = NSProcessInfo.processInfo.environment[@"BZ_FRONTLINE_USER_DIR"];
        if (!support.length) {
            NSURL *root = [NSFileManager.defaultManager URLForDirectory:NSApplicationSupportDirectory inDomain:NSUserDomainMask appropriateForURL:nil create:YES error:NULL];
            support = [root.path stringByAppendingPathComponent:@"Frontline"];
        }
        NSError *error = nil;
        if (![NSFileManager.defaultManager createDirectoryAtPath:support withIntermediateDirectories:YES attributes:nil error:&error]) {
            NSLog(@"Frontline cannot create its user folder: %@", error);
            return 1;
        }
        setenv("XDG_DATA_HOME", support.fileSystemRepresentation, 1);
        NSString *engine = [bundle.executablePath.stringByDeletingLastPathComponent stringByAppendingPathComponent:@"frontline-engine"];
        NSString *data = [resources stringByAppendingPathComponent:@"GameData"];
        /* Screenshots and diagnostics must never attempt to write inside .app. */
        if (chdir(support.fileSystemRepresentation) != 0) { perror("Frontline user folder"); return 1; }
        if (!getenv("BZ_FRONTLINE_CONSOLE")) {
            NSString *log = [support stringByAppendingPathComponent:@"latest.log"];
            if (!freopen(log.fileSystemRepresentation, "w", stderr)) { perror("Frontline log"); return 1; }
            dup2(fileno(stderr), STDOUT_FILENO);
        }
        char **args = calloc((size_t)argc + 8, sizeof(char *));
        if (!args) return 1;
        args[0] = (char *)engine.fileSystemRepresentation;
        args[1] = "-data"; args[2] = (char *)data.fileSystemRepresentation;
        int count = 3;
        bool selected = false;
        for (int i = 1; i < argc; i++)
            if (!strncmp(argv[i], "+menu_", 6) || !strcmp(argv[i], "+map") || !strcmp(argv[i], "+load") || !strcmp(argv[i], "-connect") || !strcmp(argv[i], "+connect") || !strcmp(argv[i], "+test")) selected = true;
        if (!selected) { args[count++] = "+menu_main"; }
        for (int i = 1; i < argc; i++) if (strncmp(argv[i], "-psn_", 5)) args[count++] = argv[i];
        execv(args[0], args);
        perror("Frontline launch"); free(args); return 1;
    }
}
