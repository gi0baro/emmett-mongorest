const { colors: { yellow, pink, ...colors } } = require('tailwindcss/defaultTheme')

module.exports = {
  variants: {
    borderWidth: ['responsive', 'hover', 'focus'],
    visibility: ['responsive', 'group-hover']
  },
  theme: {
    colors: colors,
    screens: {
      port: [
        {max: '779px'}
        // 919
      ],
      land: [
        {min: '780px'}
        // 920
      ]
    }
  }
}
