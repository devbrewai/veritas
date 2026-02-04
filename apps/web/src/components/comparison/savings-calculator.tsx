"use client";

import { useState } from "react";
import { Calculator, Clock, DollarSign, CheckCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// Constants for comparison
const MANUAL_HOURS_PER_CUSTOMER = 2; // 48 hours / 24 customers per day
const MANUAL_COST_PER_HOUR = 75;
const VERITAS_SECONDS_PER_CUSTOMER = 4;
const VERITAS_COST_PER_CUSTOMER = 45;

export function SavingsCalculator() {
  const [customersPerMonth, setCustomersPerMonth] = useState(100);

  // Manual process calculations
  const manualHoursTotal = customersPerMonth * MANUAL_HOURS_PER_CUSTOMER;
  const manualCostTotal = manualHoursTotal * MANUAL_COST_PER_HOUR;
  const manualDays = manualHoursTotal / 8; // 8-hour workdays

  // Veritas calculations
  const veritasMinutesTotal = (customersPerMonth * VERITAS_SECONDS_PER_CUSTOMER) / 60;
  const veritasCostTotal = customersPerMonth * VERITAS_COST_PER_CUSTOMER;

  // Savings
  const hoursSaved = manualHoursTotal - veritasMinutesTotal / 60;
  const costSaved = manualCostTotal - veritasCostTotal;
  const percentSaved = ((costSaved / manualCostTotal) * 100).toFixed(0);
  const timeSavedPercent = (
    ((manualHoursTotal - veritasMinutesTotal / 60) / manualHoursTotal) *
    100
  ).toFixed(0);

  return (
    <Card className="border-gray-200">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Calculator className="h-5 w-5 text-gray-400" />
          <CardTitle>ROI Calculator</CardTitle>
        </div>
        <CardDescription>
          See how much you can save with Veritas KYC automation
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Input */}
        <div className="space-y-2">
          <Label htmlFor="customers">Customers per Month</Label>
          <Input
            id="customers"
            type="number"
            min={1}
            max={10000}
            value={customersPerMonth}
            onChange={(e) =>
              setCustomersPerMonth(Math.max(1, parseInt(e.target.value) || 1))
            }
          />
        </div>

        {/* Comparison Table */}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Metric</TableHead>
              <TableHead className="text-right">Manual</TableHead>
              <TableHead className="text-right">Veritas</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>Time per customer</TableCell>
              <TableCell className="text-right text-gray-600">48 hours</TableCell>
              <TableCell className="text-right text-green-600 font-medium">
                4 seconds
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell>Total processing time</TableCell>
              <TableCell className="text-right text-gray-600">
                {manualHoursTotal.toLocaleString()} hours ({manualDays.toFixed(0)}{" "}
                days)
              </TableCell>
              <TableCell className="text-right text-green-600 font-medium">
                {veritasMinutesTotal.toFixed(1)} minutes
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell>Cost per customer</TableCell>
              <TableCell className="text-right text-gray-600">$150</TableCell>
              <TableCell className="text-right text-green-600 font-medium">
                $45
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell>Total monthly cost</TableCell>
              <TableCell className="text-right text-gray-600">
                ${manualCostTotal.toLocaleString()}
              </TableCell>
              <TableCell className="text-right text-green-600 font-medium">
                ${veritasCostTotal.toLocaleString()}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>

        {/* Savings Summary */}
        <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Clock className="h-4 w-4" />
              <span>Time Saved</span>
            </div>
            <div className="text-2xl font-bold text-green-600">
              {hoursSaved.toLocaleString()} hrs
            </div>
            <div className="text-sm text-gray-500">{timeSavedPercent}% faster</div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <DollarSign className="h-4 w-4" />
              <span>Cost Saved</span>
            </div>
            <div className="text-2xl font-bold text-green-600">
              ${costSaved.toLocaleString()}
            </div>
            <div className="text-sm text-gray-500">{percentSaved}% cheaper</div>
          </div>
        </div>

        {/* Key Benefits */}
        <div className="space-y-3 pt-4 border-t border-gray-100">
          <h4 className="text-sm font-medium text-gray-700">Key Benefits</h4>
          <ul className="space-y-2">
            {[
              "95% faster processing (48 hours → 4 seconds)",
              "70% cost reduction per customer",
              "Consistent ML-based risk scoring",
              "Automatic sanctions & adverse media screening",
              "SHAP-based explainability for compliance",
            ].map((benefit, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
                {benefit}
              </li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
