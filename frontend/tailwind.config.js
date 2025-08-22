/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    darkMode: 'class',
    theme: {
        // Make Space Grotesk the default sans font used by Tailwind's preflight and `font-sans`
        fontFamily: {
            sans: [
                'Space Grotesk',
                '-apple-system',
                'BlinkMacSystemFont',
                'Segoe UI',
                'Roboto',
                'Helvetica Neue',
                'Arial',
                'sans-serif',
            ],
        },
        extend: {},
    },
    plugins: [],
} 