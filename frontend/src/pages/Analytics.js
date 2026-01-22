import { useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { TrendingUp, DollarSign, Clock, Target, BarChart3 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const COLORS = ['#0F172A', '#3B82F6', '#10B981', '#F59E0B', '#EF4444'];

export const Analytics = () => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/analytics`);
      setAnalytics(response.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
      toast.error('Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (!analytics) return null;

  const statusData = Object.entries(analytics.status_distribution).map(([name, value]) => ({
    name,
    value
  }));

  return (
    <div className="p-8" data-testid="analytics-page">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="font-outfit text-4xl font-semibold tracking-tight text-slate-900 mb-2">
            Analytics Dashboard
          </h1>
          <p className="text-slate-600">Track your proposal performance and optimize your sales process</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="border-slate-200 shadow-sm hover:shadow-md transition-shadow duration-300">
            <CardHeader className="pb-3">
              <CardDescription className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                Acceptance Rate
              </CardDescription>
              <CardTitle className="text-3xl font-outfit font-semibold text-emerald-600">
                {analytics.acceptance_rate}%
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center text-sm text-slate-600">
                <Target className="h-4 w-4 mr-2" strokeWidth={1.5} />
                Win rate
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm hover:shadow-md transition-shadow duration-300">
            <CardHeader className="pb-3">
              <CardDescription className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                Avg Deal Size
              </CardDescription>
              <CardTitle className="text-3xl font-outfit font-semibold text-blue-600">
                ${analytics.avg_deal_size.toLocaleString()}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center text-sm text-slate-600">
                <DollarSign className="h-4 w-4 mr-2" strokeWidth={1.5} />
                Per proposal
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm hover:shadow-md transition-shadow duration-300">
            <CardHeader className="pb-3">
              <CardDescription className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                Avg Time to Close
              </CardDescription>
              <CardTitle className="text-3xl font-outfit font-semibold text-orange-600">
                {analytics.avg_time_to_close} days
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center text-sm text-slate-600">
                <Clock className="h-4 w-4 mr-2" strokeWidth={1.5} />
                Sales cycle
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm hover:shadow-md transition-shadow duration-300">
            <CardHeader className="pb-3">
              <CardDescription className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                Total Revenue
              </CardDescription>
              <CardTitle className="text-3xl font-outfit font-semibold text-slate-900">
                ${analytics.total_revenue.toLocaleString()}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center text-sm text-slate-600">
                <TrendingUp className="h-4 w-4 mr-2" strokeWidth={1.5} />
                Closed deals
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="border-slate-200 shadow-sm">
            <CardHeader>
              <CardTitle className="font-outfit text-2xl font-semibold text-slate-900">
                Status Distribution
              </CardTitle>
              <CardDescription>Breakdown of proposals by status</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={statusData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {statusData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm">
            <CardHeader>
              <CardTitle className="font-outfit text-2xl font-semibold text-slate-900">
                Proposal Pipeline
              </CardTitle>
              <CardDescription>Volume by status stage</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={statusData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="name" stroke="#64748B" fontSize={12} />
                  <YAxis stroke="#64748B" fontSize={12} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#0F172A" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        <Card className="border-slate-200 shadow-sm mt-6">
          <CardHeader>
            <CardTitle className="font-outfit text-2xl font-semibold text-slate-900">
              Key Insights
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-start gap-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <BarChart3 className="h-6 w-6 text-blue-600 mt-1" />
              <div>
                <h4 className="font-semibold text-slate-900 mb-1">Proposal Volume</h4>
                <p className="text-sm text-slate-600">
                  You've created {analytics.total_proposals} proposals. Keep the momentum going to increase your success rate.
                </p>
              </div>
            </div>
            {analytics.acceptance_rate > 0 && (
              <div className="flex items-start gap-4 p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
                <Target className="h-6 w-6 text-emerald-600 mt-1" />
                <div>
                  <h4 className="font-semibold text-slate-900 mb-1">Win Rate Performance</h4>
                  <p className="text-sm text-slate-600">
                    Your acceptance rate of {analytics.acceptance_rate}% shows {analytics.acceptance_rate > 30 ? 'strong' : 'developing'} performance. 
                    {analytics.acceptance_rate < 30 && ' Consider reviewing successful proposals to identify winning patterns.'}
                  </p>
                </div>
              </div>
            )}
            {analytics.avg_time_to_close > 0 && (
              <div className="flex items-start gap-4 p-4 bg-orange-50 border border-orange-200 rounded-lg">
                <Clock className="h-6 w-6 text-orange-600 mt-1" />
                <div>
                  <h4 className="font-semibold text-slate-900 mb-1">Sales Cycle Timing</h4>
                  <p className="text-sm text-slate-600">
                    Average time to close is {analytics.avg_time_to_close} days. {analytics.avg_time_to_close > 30 ? 'Consider strategies to accelerate your sales cycle.' : 'Your sales cycle is efficient!'}
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Analytics;