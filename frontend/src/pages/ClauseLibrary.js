import { useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Plus, Trash2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const ClauseLibrary = () => {
  const [clauses, setClauses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [newClause, setNewClause] = useState({
    title: '',
    content: '',
    category: 'Legal',
    is_custom: true
  });

  useEffect(() => {
    fetchClauses();
  }, []);

  const fetchClauses = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/clauses`);
      setClauses(response.data);
    } catch (error) {
      console.error('Error fetching clauses:', error);
      toast.error('Failed to load clauses');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateClause = async (e) => {
    e.preventDefault();
    
    if (!newClause.title || !newClause.content) {
      toast.error('Please fill in all fields');
      return;
    }

    try {
      await axios.post(`${API}/clauses`, newClause);
      toast.success('Clause created successfully');
      setOpen(false);
      setNewClause({
        title: '',
        content: '',
        category: 'Legal',
        is_custom: true
      });
      fetchClauses();
    } catch (error) {
      console.error('Error creating clause:', error);
      toast.error('Failed to create clause');
    }
  };

  const handleDeleteClause = async (clauseId) => {
    try {
      await axios.delete(`${API}/clauses/${clauseId}`);
      toast.success('Clause deleted successfully');
      fetchClauses();
    } catch (error) {
      console.error('Error deleting clause:', error);
      toast.error('Failed to delete clause');
    }
  };

  const getCategoryColor = (category) => {
    const colors = {
      'Legal': 'bg-blue-50 text-blue-700 border-blue-200',
      'Financial': 'bg-emerald-50 text-emerald-700 border-emerald-200',
      'Service': 'bg-purple-50 text-purple-700 border-purple-200',
      'Project Management': 'bg-orange-50 text-orange-700 border-orange-200'
    };
    return colors[category] || 'bg-slate-100 text-slate-700 border-slate-200';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading clauses...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8" data-testid="clause-library-page">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="font-outfit text-4xl font-semibold tracking-tight text-slate-900 mb-2">
              Clause Library
            </h1>
            <p className="text-slate-600">Manage pre-defined and custom clauses for your proposals</p>
          </div>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button className="bg-slate-900 text-white hover:bg-slate-800" data-testid="add-clause-button">
                <Plus className="h-4 w-4 mr-2" />
                Add Clause
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle className="font-outfit text-2xl font-semibold">Create New Clause</DialogTitle>
                <DialogDescription>
                  Add a custom clause to your library that can be reused in proposals
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreateClause}>
                <div className="space-y-4 py-4">
                  <div>
                    <Label htmlFor="title" className="text-slate-700 font-medium mb-2">
                      Title *
                    </Label>
                    <Input
                      id="title"
                      value={newClause.title}
                      onChange={(e) => setNewClause({ ...newClause, title: e.target.value })}
                      placeholder="Clause title"
                      className="border-slate-200"
                      data-testid="clause-title-input"
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="category" className="text-slate-700 font-medium mb-2">
                      Category *
                    </Label>
                    <Select
                      value={newClause.category}
                      onValueChange={(value) => setNewClause({ ...newClause, category: value })}
                    >
                      <SelectTrigger className="border-slate-200" data-testid="clause-category-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Legal">Legal</SelectItem>
                        <SelectItem value="Financial">Financial</SelectItem>
                        <SelectItem value="Service">Service</SelectItem>
                        <SelectItem value="Project Management">Project Management</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="content" className="text-slate-700 font-medium mb-2">
                      Content *
                    </Label>
                    <Textarea
                      id="content"
                      value={newClause.content}
                      onChange={(e) => setNewClause({ ...newClause, content: e.target.value })}
                      placeholder="Clause content"
                      className="border-slate-200 min-h-32"
                      data-testid="clause-content-input"
                      required
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button type="button" variant="outline" onClick={() => setOpen(false)} data-testid="cancel-clause-button">
                    Cancel
                  </Button>
                  <Button type="submit" className="bg-slate-900 text-white hover:bg-slate-800" data-testid="save-clause-button">
                    Save Clause
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {clauses.map((clause) => (
            <Card 
              key={clause.id} 
              className="border-slate-200 hover:shadow-md transition-shadow duration-200"
              data-testid={`clause-card-${clause.id}`}
            >
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <CardTitle className="font-outfit text-xl font-semibold text-slate-900">
                        {clause.title}
                      </CardTitle>
                      <Badge className={`${getCategoryColor(clause.category)} status-badge`}>
                        {clause.category}
                      </Badge>
                      {clause.is_custom && (
                        <Badge className="bg-slate-100 text-slate-700 border-slate-200 status-badge">
                          Custom
                        </Badge>
                      )}
                    </div>
                  </div>
                  {clause.is_custom && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteClause(clause.id)}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      data-testid={`delete-clause-${clause.id}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-slate-600 leading-relaxed">{clause.content}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {clauses.length === 0 && (
          <Card className="border-slate-200">
            <CardContent className="p-12 text-center">
              <p className="text-slate-600 mb-4">No clauses found</p>
              <Button onClick={() => setOpen(true)} variant="outline">
                <Plus className="h-4 w-4 mr-2" />
                Add your first clause
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default ClauseLibrary;