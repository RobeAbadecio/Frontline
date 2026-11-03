local elapsed = 0
function ow3_update(msec) elapsed = elapsed + msec end
function ow3_draw()
    assert(ow3.player == nil and ow3.stat == nil and ow3.inventory == nil and ow3.actions == nil)
    ow3.draw_image('Interface\\Test\\LuaPanel.blp', 0.1, 0.2, 0.3, 0.05)
    ow3.draw_image('Interface\\Test\\Inventory.blp', 0.14, 0.26, 0.04, 0.04)
    ow3.draw_color(0.2, 0.32, 0.12, 0.02, 10, 20, 30, 240)
    ow3.draw_text('Login:' .. elapsed, 0.21, 0.35, 0.4, 0.03, 13, 255, 220, 120, 255, 'center')
end
function ow3_handle_text_input(text) end
function ow3_handle_mouse_click(x, y, button) end
function ow3_handle_mouse_move(x, y) end
