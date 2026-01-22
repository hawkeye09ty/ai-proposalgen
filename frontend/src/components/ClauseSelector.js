import { useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const ClauseSelector = ({ selectedClauses, onClausesChange }) => {
  const [clauses, setClauses] = useState([]);
  const [loading, setLoading] = useState(true);

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

  const handleToggleClause = (clauseId) => {
    const newSelection = selectedClauses.includes(clauseId)
      ? selectedClauses.filter(id => id !== clauseId)
      : [...selectedClauses, clauseId];
    onClausesChange(newSelection);
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
    return <div className="text-slate-600">Loading clauses...</div>;
  }

  if (clauses.length === 0) {
    return (
      <div className="text-center py-8 text-slate-600">
        No clauses available. Add some in the Clause Library first.
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid="clause-selector">
      {clauses.map((clause) => (
        <Card
          key={clause.id}
          className={`p-4 cursor-pointer border-slate-200 hover:border-blue-300 transition-colors ${
            selectedClauses.includes(clause.id) ? 'border-blue-400 bg-blue-50/30' : ''
          }`}
          onClick={() => handleToggleClause(clause.id)}
          data-testid={`clause-option-${clause.id}`}
        >
          <div className="flex items-start gap-3">
            <Checkbox
              checked={selectedClauses.includes(clause.id)}
              onCheckedChange={() => handleToggleClause(clause.id)}
              className="mt-1"
              data-testid={`clause-checkbox-${clause.id}`}
            />
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Label className="font-semibold text-slate-900 cursor-pointer">
                  {clause.title}
                </Label>
                <Badge className={`${getCategoryColor(clause.category)} status-badge text-xs`}>
                  {clause.category}
                </Badge>
              </div>
              <p className="text-sm text-slate-600 leading-relaxed">{clause.content}</p>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
};

export default ClauseSelector;