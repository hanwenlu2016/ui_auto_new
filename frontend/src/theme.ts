import { GlobalThemeOverrides } from 'naive-ui'

export const adminTheme: GlobalThemeOverrides = {
    common: {
        primaryColor: '#2d8cf0',
        primaryColorHover: '#57a3f3',
        primaryColorPressed: '#2061a5',
        primaryColorSuppl: '#2d8cf0',
        borderRadius: '4px',
        fontFamily: 'v-sans, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol"'
    },
    Card: {
        borderRadius: '8px',
        boxShadow: '0 1px 2px -2px rgba(0, 0, 0, 0.08), 0 3px 6px 0 rgba(0, 0, 0, 0.06), 0 5px 12px 4px rgba(0, 0, 0, 0.04)'
    },
    Button: {
        borderRadius: '4px',
        fontWeight: '500'
    },
    Menu: {
        itemColorActive: '#e6f7ff',
        itemColorActiveHover: '#e6f7ff',
        itemTextColorActive: '#2d8cf0',
        itemIconColorActive: '#2d8cf0',
        itemBorderRadius: '4px'
    }
}
