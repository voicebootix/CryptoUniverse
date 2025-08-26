import React, { useState } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore, useUser } from '@/store/authStore';
import {
  LayoutDashboard,
  TrendingUp,
  Wallet,
  Bot,
  Settings,
  Users,
  Menu,
  X,
  Bell,
  User,
  LogOut,
  Shield,
  Activity,
  BarChart3,
  Zap,
  AlertTriangle,
  ChevronDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { getInitials } from '@/lib/utils';

interface NavigationItem {
  name: string;
  href: string;
  icon: React.ComponentType<any>;
  badge?: string;
  adminOnly?: boolean;
}

const navigation: NavigationItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Trading', href: '/dashboard/trading', icon: TrendingUp },
  { name: 'Portfolio', href: '/dashboard/portfolio', icon: Wallet },
  { name: 'Autonomous', href: '/dashboard/autonomous', icon: Bot, badge: 'AI' },
  { name: 'Exchanges', href: '/dashboard/exchanges', icon: BarChart3 },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings },
  { name: 'Admin', href: '/dashboard/admin', icon: Users, adminOnly: true },
];

const DashboardLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const user = useUser();
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = () => {
    logout();
    navigate('/auth/login');
  };

  const filteredNavigation = navigation.filter(
    (item) => !item.adminOnly || user?.role === 'admin'
  );

  const isActivePath = (href: string) => {
    if (href === '/dashboard') {
      return location.pathname === href;
    }
    return location.pathname.startsWith(href);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile sidebar overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 lg:hidden"
          >
            <div 
              className="absolute inset-0 bg-black/20 backdrop-blur-sm"
              onClick={() => setSidebarOpen(false)}
            />
            <motion.div
              initial={{ x: -320 }}
              animate={{ x: 0 }}
              exit={{ x: -320 }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
              className="absolute left-0 top-0 h-full w-80 bg-card border-r border-border shadow-xl"
            >
              <SidebarContent 
                navigation={filteredNavigation}
                isActivePath={isActivePath}
                onClose={() => setSidebarOpen(false)}
                user={user}
                onLogout={handleLogout}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-80 lg:flex-col">
        <SidebarContent 
          navigation={filteredNavigation}
          isActivePath={isActivePath}
          user={user}
          onLogout={handleLogout}
        />
      </div>

      {/* Main content */}
      <div className="lg:pl-80">
        {/* Top header */}
        <header className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8">
          {/* Mobile menu button */}
          <Button
            variant="ghost"
            size="icon"
            className="-m-2.5 p-2.5 lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-6 w-6" />
          </Button>

          {/* Breadcrumb */}
          <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
            <div className="flex items-center">
              <nav className="flex text-sm">
                <span className="text-muted-foreground">
                  {navigation.find(item => isActivePath(item.href))?.name || 'Dashboard'}
                </span>
              </nav>
            </div>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-x-4 lg:gap-x-6">
            {/* System status indicator */}
            <div className="flex items-center gap-2">
              <div className="status-indicator status-online">
                <div className="h-3 w-3 bg-profit rounded-full" />
              </div>
              <span className="text-xs text-muted-foreground hidden sm:block">
                System Online
              </span>
            </div>

            {/* Notifications */}
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5" />
              <Badge
                variant="destructive"
                className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs"
              >
                3
              </Badge>
            </Button>

            {/* User menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                  <Avatar className="h-8 w-8">
                    <AvatarImage src={user?.avatar_url} alt={user?.full_name} />
                    <AvatarFallback>
                      {user ? getInitials(user.full_name) : 'U'}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-56" align="end" forceMount>
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">
                      {user?.full_name}
                    </p>
                    <p className="text-xs leading-none text-muted-foreground">
                      {user?.email}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link to="/dashboard/settings">
                    <User className="mr-2 h-4 w-4" />
                    Profile
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link to="/dashboard/settings">
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </Link>
                </DropdownMenuItem>
                {user?.role === 'admin' && (
                  <DropdownMenuItem asChild>
                    <Link to="/dashboard/admin">
                      <Shield className="mr-2 h-4 w-4" />
                      Admin Panel
                    </Link>
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page content */}
        <main className="py-6">
          <div className="px-4 sm:px-6 lg:px-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

interface SidebarContentProps {
  navigation: NavigationItem[];
  isActivePath: (href: string) => boolean;
  onClose?: () => void;
  user: any;
  onLogout: () => void;
}

const SidebarContent: React.FC<SidebarContentProps> = ({
  navigation,
  isActivePath,
  onClose,
  user,
  onLogout,
}) => {
  return (
    <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-card border-r border-border px-6 pb-4">
      {/* Logo and close button */}
      <div className="flex h-16 shrink-0 items-center justify-between">
        <Link to="/dashboard" className="flex items-center space-x-2">
          <div className="p-2 bg-primary/10 rounded-lg">
            <TrendingUp className="h-6 w-6 text-primary" />
          </div>
          <div className="flex flex-col">
            <span className="text-lg font-bold">CryptoUniverse</span>
            <span className="text-xs text-muted-foreground">AI Money Manager</span>
          </div>
        </Link>
        
        {onClose && (
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-6 w-6" />
          </Button>
        )}
      </div>

      {/* User info */}
      <div className="mx-2 p-3 rounded-lg bg-muted/50 border border-muted">
        <div className="flex items-center space-x-3">
          <Avatar className="h-10 w-10">
            <AvatarImage src={user?.avatar_url} alt={user?.full_name} />
            <AvatarFallback>
              {user ? getInitials(user.full_name) : 'U'}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">
              {user?.full_name}
            </p>
            <div className="flex items-center space-x-2">
              <Badge variant="secondary" className="text-xs">
                {user?.role}
              </Badge>
              {user?.simulation_mode && (
                <Badge variant="outline" className="text-xs">
                  Simulation
                </Badge>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col">
        <ul role="list" className="flex flex-1 flex-col gap-y-2">
          {navigation.map((item) => {
            const isActive = isActivePath(item.href);
            return (
              <li key={item.name}>
                <Link
                  to={item.href}
                  onClick={onClose}
                  className={`
                    group flex gap-x-3 rounded-md p-3 text-sm leading-6 font-semibold transition-all duration-200
                    ${isActive
                      ? 'bg-primary text-primary-foreground shadow-md'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                    }
                  `}
                >
                  <item.icon
                    className={`h-5 w-5 shrink-0 transition-colors ${
                      isActive ? 'text-primary-foreground' : 'text-muted-foreground group-hover:text-foreground'
                    }`}
                  />
                  <span className="flex-1">{item.name}</span>
                  {item.badge && (
                    <Badge 
                      variant={isActive ? "secondary" : "outline"} 
                      className="text-xs"
                    >
                      {item.badge}
                    </Badge>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Bottom section */}
        <div className="mt-auto space-y-2">
          {/* Trading mode indicator */}
          <div className="mx-2 p-3 rounded-lg bg-muted/30 border border-muted">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Activity className="h-4 w-4 text-profit" />
                <span className="text-sm font-medium">Trading Status</span>
              </div>
              <Badge variant="outline" className="text-xs">
                {user?.simulation_mode ? 'Simulation' : 'Live'}
              </Badge>
            </div>
          </div>

          {/* System status */}
          <div className="mx-2 p-3 rounded-lg bg-muted/30 border border-muted">
            <div className="flex items-center space-x-2">
              <div className="status-indicator status-online">
                <div className="h-2 w-2 bg-profit rounded-full" />
              </div>
              <span className="text-xs text-muted-foreground">All systems operational</span>
            </div>
          </div>
        </div>
      </nav>
    </div>
  );
};

export default DashboardLayout;
