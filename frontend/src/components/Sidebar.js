import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, FileText, Plus, Library, BarChart3, Settings } from 'lucide-react';

export const Sidebar = () => {
  const location = useLocation();

  const navItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/create', icon: Plus, label: 'Create Proposal' },
    { path: '/clauses', icon: Library, label: 'Clause Library' },
    { path: '/analytics', icon: BarChart3, label: 'Analytics' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ];

  const isActive = (path) => location.pathname === path;

  return (
    <aside className="w-64 bg-slate-900 text-white flex flex-col" data-testid="sidebar">
      <div className="p-6 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <FileText className="h-8 w-8 text-blue-400" strokeWidth={1.5} />
          <div>
            <h1 className="font-outfit text-xl font-semibold">ProposalAI</h1>
            <p className="text-xs text-slate-400">Smart Proposals</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4" data-testid="sidebar-nav">
        <ul className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  data-testid={`nav-${item.label.toLowerCase().replace(' ', '-')}`}
                  className={`flex items-center gap-3 px-4 py-3 rounded-md transition-all duration-200 ${
                    isActive(item.path)
                      ? 'bg-slate-800 text-white'
                      : 'text-slate-300 hover:bg-slate-800/50 hover:text-white'
                  }`}
                >
                  <Icon className="h-5 w-5" strokeWidth={1.5} />
                  <span className="font-medium">{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="p-4 border-t border-slate-800">
        <div className="text-xs text-slate-400">
          <p className="font-semibold mb-1">Built with AI</p>
          <p>Powered by GPT-5.2</p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;