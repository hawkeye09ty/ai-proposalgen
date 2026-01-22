import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { FileText, Plus, TrendingUp, Clock, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const Dashboard = () => {
  const [proposals, setProposals] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState('all');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [proposalsRes, statsRes] = await Promise.all([
        axios.get(`${API}/proposals`),
        axios.get(`${API}/stats`)
      ]);
      setProposals(proposalsRes.data);
      setStats(statsRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadgeClass = (status) => {
    const classes = {
      'Draft': 'bg-slate-100 text-slate-700 border-slate-200',
      'Pending Review': 'bg-amber-50 text-amber-700 border-amber-200',
      'Sent': 'bg-blue-50 text-blue-700 border-blue-200',
      'Accepted': 'bg-emerald-50 text-emerald-700 border-emerald-200',
      'Rejected': 'bg-red-50 text-red-700 border-red-200'
    };
    return classes[status] || classes['Draft'];
  };

  const filteredProposals = activeFilter === 'all' 
    ? proposals 
    : proposals.filter(p => p.status === activeFilter);

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8" data-testid="dashboard-page">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="font-outfit text-4xl font-semibold tracking-tight text-slate-900 mb-2">
              Dashboard
            </h1>
            <p className="text-slate-600">Manage and track all your proposals</p>
          </div>
          <Link to="/create">
            <Button className="bg-slate-900 text-white hover:bg-slate-800 shadow-sm hover:shadow-md transition-all duration-200" data-testid="create-proposal-button">
              <Plus className="h-4 w-4 mr-2" />
              Create Proposal
            </Button>
          </Link>
        </div>

        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <Card className="border-slate-200 shadow-sm hover:shadow-md transition-shadow duration-300">
              <CardHeader className="pb-3">
                <CardDescription className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                  Total Proposals
                </CardDescription>
                <CardTitle className="text-3xl font-outfit font-semibold text-slate-900">
                  {stats.total}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center text-sm text-slate-600">
                  <FileText className="h-4 w-4 mr-2" strokeWidth={1.5} />
                  All time
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-200 shadow-sm hover:shadow-md transition-shadow duration-300">
              <CardHeader className="pb-3">
                <CardDescription className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                  In Progress
                </CardDescription>
                <CardTitle className="text-3xl font-outfit font-semibold text-slate-900">
                  {stats.draft + stats.pending_review}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center text-sm text-slate-600">
                  <Clock className="h-4 w-4 mr-2" strokeWidth={1.5} />
                  Draft & Pending
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-200 shadow-sm hover:shadow-md transition-shadow duration-300">
              <CardHeader className="pb-3">
                <CardDescription className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                  Accepted
                </CardDescription>
                <CardTitle className="text-3xl font-outfit font-semibold text-emerald-600">
                  {stats.accepted}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center text-sm text-emerald-600">
                  <CheckCircle className="h-4 w-4 mr-2" strokeWidth={1.5} />
                  Won deals
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-200 shadow-sm hover:shadow-md transition-shadow duration-300">
              <CardHeader className="pb-3">
                <CardDescription className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                  Sent
                </CardDescription>
                <CardTitle className="text-3xl font-outfit font-semibold text-blue-600">
                  {stats.sent}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center text-sm text-blue-600">
                  <TrendingUp className="h-4 w-4 mr-2" strokeWidth={1.5} />
                  Awaiting response
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        <Card className="border-slate-200 shadow-sm">
          <CardHeader>
            <CardTitle className="font-outfit text-2xl font-semibold text-slate-900">
              All Proposals
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="all" onValueChange={setActiveFilter} data-testid="filter-tabs">
              <TabsList className="mb-6">
                <TabsTrigger value="all" data-testid="filter-all">All</TabsTrigger>
                <TabsTrigger value="Draft" data-testid="filter-draft">Draft</TabsTrigger>
                <TabsTrigger value="Pending Review" data-testid="filter-pending">Pending Review</TabsTrigger>
                <TabsTrigger value="Sent" data-testid="filter-sent">Sent</TabsTrigger>
                <TabsTrigger value="Accepted" data-testid="filter-accepted">Accepted</TabsTrigger>
                <TabsTrigger value="Rejected" data-testid="filter-rejected">Rejected</TabsTrigger>
              </TabsList>

              <TabsContent value={activeFilter} className="space-y-4">
                {filteredProposals.length === 0 ? (
                  <div className="text-center py-12" data-testid="no-proposals">
                    <FileText className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                    <p className="text-slate-600 mb-4">No proposals found</p>
                    <Link to="/create">
                      <Button variant="outline" data-testid="create-first-proposal">
                        <Plus className="h-4 w-4 mr-2" />
                        Create your first proposal
                      </Button>
                    </Link>
                  </div>
                ) : (
                  filteredProposals.map((proposal) => (
                    <Link to={`/proposals/${proposal.id}`} key={proposal.id}>
                      <Card 
                        className="border-slate-200 hover:border-blue-300 hover:ring-1 hover:ring-blue-100 transition-all duration-200 cursor-pointer"
                        data-testid={`proposal-card-${proposal.id}`}
                      >
                        <CardContent className="p-6">
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <div className="flex items-center gap-3 mb-2">
                                <h3 className="font-outfit text-lg font-semibold text-slate-900">
                                  {proposal.client_name}
                                </h3>
                                <Badge className={`status-badge ${getStatusBadgeClass(proposal.status)}`}>
                                  {proposal.status}
                                </Badge>
                              </div>
                              <p className="text-slate-600 mb-3 line-clamp-2">
                                {proposal.project_description}
                              </p>
                              <div className="flex gap-6 text-sm text-slate-500">
                                <div>
                                  <span className="font-medium">Budget:</span> {proposal.budget_range}
                                </div>
                                <div>
                                  <span className="font-medium">Timeline:</span> {proposal.timeline}
                                </div>
                                <div>
                                  <span className="font-medium">Created:</span> {formatDate(proposal.created_at)}
                                </div>
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </Link>
                  ))
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;