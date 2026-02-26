import React, { useState } from 'react';
import { Card } from '../ui/Card';
import { ImportWizard } from './ImportWizard';
import { FileText, PlusCircle } from 'lucide-react';
import { Button } from '../ui/Button';

export const ContactImport: React.FC = () => {
    const [showWizard, setShowWizard] = useState(false);

    if (showWizard) {
        return (
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <h3 className="text-xl font-bold text-slate-200">Import Contacts</h3>
                    <Button variant="ghost" onClick={() => setShowWizard(false)}>Cancel</Button>
                </div>
                <ImportWizard onComplete={() => setShowWizard(false)} />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <Card className="p-12 flex flex-col items-center justify-center text-center gap-6 bg-slate-900/40 border-slate-800">
                <div className="w-20 h-20 rounded-2xl bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20">
                    <FileText className="w-10 h-10 text-indigo-400" />
                </div>
                <div>
                    <h3 className="text-2xl font-bold text-slate-200">Grow your audience</h3>
                    <p className="text-slate-400 max-w-sm mx-auto mt-2">
                        Import your contacts from any CSV file. Our intelligent mapper will automatically match your columns to our system.
                    </p>
                </div>
                <Button
                    size="lg"
                    leftIcon={<PlusCircle className="w-5 h-5" />}
                    onClick={() => setShowWizard(true)}
                >
                    Start Importing
                </Button>
            </Card>
        </div>
    );
};
