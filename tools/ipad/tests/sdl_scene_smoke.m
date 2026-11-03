/* Retail-data-free platform probe: exercise the patched SDL window/GLES path. */
#include <SDL2/SDL.h>
#include <SDL2/SDL_syswm.h>
#import <UIKit/UIKit.h>
#include <OpenGLES/ES3/gl.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    SDL_Window *window;
    SDL_GLContext context;
    int width, height;
    int last_width = 0, last_height = 0;
    unsigned char pixel[4];
    if (SDL_Init(SDL_INIT_VIDEO) != 0) goto fail;
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_ES);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
    window = SDL_CreateWindow("SDL scene probe", 0, 0, 800, 600,
                              SDL_WINDOW_OPENGL | SDL_WINDOW_ALLOW_HIGHDPI | SDL_WINDOW_RESIZABLE);
    if (!window) goto fail;
    context = SDL_GL_CreateContext(window);
    if (!context) goto fail;
    SDL_GL_GetDrawableSize(window, &width, &height);
    if (width <= 0 || height <= 0) goto fail;
    fprintf(stderr, "SCENE_SMOKE drawable=%dx%d\n", width, height);
    for (int frame = 0; frame < 600; frame++) {
        SDL_Event event;
        while (SDL_PollEvent(&event)) { if (event.type == SDL_QUIT) exit(2); }
        SDL_GL_GetDrawableSize(window, &width, &height);
        if (frame > 10) {
            SDL_SysWMinfo info;
            SDL_VERSION(&info.version);
            if (!SDL_GetWindowWMInfo(window, &info)) goto fail;
            UIWindow *native = info.info.uikit.window;
            CGSize scene = native.windowScene.coordinateSpace.bounds.size;
            int logical_width, logical_height;
            SDL_GetWindowSize(window, &logical_width, &logical_height);
            if (logical_width != (int)scene.width || logical_height != (int)scene.height ||
                width != (int)(scene.width * native.screen.scale) ||
                height != (int)(scene.height * native.screen.scale)) {
                fprintf(stderr, "SCENE_SMOKE FAIL geometry scene=%.0fx%.0f logical=%dx%d drawable=%dx%d\n",
                    scene.width, scene.height, logical_width, logical_height, width, height);
                exit(1);
            }
        }
        if (width != last_width || height != last_height) {
            fprintf(stderr, "SCENE_SMOKE resized=%dx%d\n", width, height);
            last_width = width; last_height = height;
        }
        glViewport(0, 0, width, height);
        glClearColor(0.0f, 1.0f, 0.0f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);
        glReadPixels(width / 2, height / 2, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, pixel);
        if (glGetError() != GL_NO_ERROR || pixel[0] != 0 || pixel[1] != 255 || pixel[2] != 0) {
            fprintf(stderr, "SCENE_SMOKE bad framebuffer\n");
            exit(1);
        }
        SDL_GL_SwapWindow(window);
        SDL_Delay(16);
    }
    SDL_GL_DeleteContext(context);
    SDL_DestroyWindow(window);
    SDL_Quit();
    fprintf(stderr, "SCENE_SMOKE PASS: 600 presented green frames\n");
    exit(0);
fail:
    fprintf(stderr, "SCENE_SMOKE FAIL: %s\n", SDL_GetError());
    exit(1);
}
