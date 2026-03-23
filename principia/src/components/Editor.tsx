
interface EditorProps {
  value: string;
  onChange: (val: string) => void;
}

export function Editor({ value, onChange }: EditorProps) {
  return (
    <div className="h-full w-full bg-background p-8 flex flex-col border-r border-border">
      <div className="mb-4 flex items-center gap-2 text-muted-foreground text-xs uppercase tracking-widest font-semibold">
        <span className="w-2 h-2 rounded-full bg-blue-500"></span>
        Source Input
      </div>
      <textarea
        className="w-full h-full bg-transparent text-foreground resize-none outline-none font-mono text-sm leading-7 placeholder:text-muted-foreground/50 custom-scrollbar overflow-y-auto"
        placeholder="# Newtonian Mechanics
        
Consider a particle of mass $m$ moving under the influence of a potential $V(x)$. 
The Lagrangian is given by:

$$ L = T - V = \frac{1}{2}m\dot{x}^2 - V(x) $$

The equation of motion is derived from Euler-Lagrange equation..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
      />
    </div>
  );
}
