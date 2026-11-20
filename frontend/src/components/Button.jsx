export default function Button({ variant = "secondary", className = "", children, ...props }) {
    return (
        <button type="button" className={`btn btn-${variant} ${className}`.trim()} {...props}>
            {children}
        </button>
    );
}
