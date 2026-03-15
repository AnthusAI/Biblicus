/** @type {import('tailwindcss').Config} */
export default {
    darkMode: ["class"],
    content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./node_modules/springstack/dist/**/*.{js,mjs}",
    "../../Springstack/packages/springstack/src/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
  	extend: {
  		borderRadius: {
  			DEFAULT: '0.25rem',
  			sm: '0.125rem',
  			md: '0.25rem',
  			lg: '0.375rem',
  			xl: '0.5rem',
  			'2xl': '0.75rem',
  			full: '9999px'
  		},
  		boxShadow: {
            DEFAULT: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  			sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  			md: '0 4px 6px -1px rgb(0 0 0 / 0.1)', // We might want to flatten this further
  			lg: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
            flat: '0 2px 0 0 rgb(0 0 0 / 0.05)', // Custom flat shadow
            'flat-muted': '2px 2px 0 0 color-mix(in srgb, var(--muted-foreground) 15%, transparent)', // 45-degree flat shadow
  			none: 'none',
  		},
  		colors: {
  			background: 'var(--background)',
  			foreground: 'var(--foreground)',
  			card: {
  				DEFAULT: 'var(--card)',
  				foreground: 'var(--card-foreground)'
  			},
  			popover: {
  				DEFAULT: 'var(--popover)',
  				foreground: 'var(--popover-foreground)'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'var(--muted)',
  				foreground: 'var(--muted-foreground)'
  			},
  			accent: {
  				DEFAULT: 'var(--accent)',
  				foreground: 'var(--accent-foreground)'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'var(--border)',
  			input: 'var(--input)',
  			ring: 'var(--ring)',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			},
            status: {
                true: {
                    DEFAULT: 'hsl(var(--status-true))',
                    foreground: 'hsl(var(--status-true-foreground))'
                },
                false: {
                    DEFAULT: 'hsl(var(--status-false))',
                    foreground: 'hsl(var(--status-false-foreground))'
                },
                danger: {
                    DEFAULT: 'hsl(var(--status-danger))',
                    foreground: 'hsl(var(--status-danger-foreground))'
                },
                warning: {
                    DEFAULT: 'hsl(var(--status-warning))',
                    foreground: 'hsl(var(--status-warning-foreground))'
                }
            },
            /* New Selector Colors */
            'secondary-muted': 'hsl(var(--secondary-muted))',
            'primary-text': 'hsl(var(--primary-text))',
            hover: 'var(--hover)',
            selected: {
                DEFAULT: 'var(--selected)',
                foreground: 'var(--selected-foreground)'
            },
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
}
