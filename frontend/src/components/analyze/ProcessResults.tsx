import React from 'react';
import { Card, CardBody, CardTitle, Button, Row, Col, Progress, Table } from 'reactstrap';
import type { Environment, Process } from '../../models';

interface ProcessResultsProps {
  environment: Environment;
  process: Process;
  results: {
    overall_adherence: number;
    completion_adherence: number;
    timing_adherence: number;
    completed_steps: number;
    total_steps: number;
    total_time: number;
    target_total_time: number;
    step_details: Array<{
      stepNumber: number;
      stepName: string;
      completedAt: number;
      duration: number;
      targetDuration: number;
    }>;
  };
  onRestart: () => void;
  onNewProcess: () => void;
}

const ProcessResults: React.FC<ProcessResultsProps> = ({
  environment,
  process,
  results,
  onRestart,
  onNewProcess
}) => {
  const getScoreColor = (score: number) => {
    if (score >= 90) return 'success';
    if (score >= 70) return 'warning';
    return 'danger';
  };

  const getScoreLabel = (score: number) => {
    if (score >= 90) return 'Excellent';
    if (score >= 80) return 'Good';
    if (score >= 70) return 'Fair';
    if (score >= 60) return 'Poor';
    return 'Needs Improvement';
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  const getTimingStatus = (actual: number, target: number) => {
    const ratio = actual / target;
    if (ratio <= 1.1) return { color: 'success', label: 'On Time' };
    if (ratio <= 1.5) return { color: 'warning', label: 'Slow' };
    return { color: 'danger', label: 'Very Slow' };
  };

  return (
    <div>
      {/* Header */}
      <Card className="mb-4">
        <CardBody>
          <Row className="align-items-center">
            <Col>
              <CardTitle tag="h4">Process Analysis Results</CardTitle>
              <p className="text-muted mb-0">
                Analysis complete for <strong>{process.ProcessName}</strong> in <strong>{environment.Name}</strong>
              </p>
            </Col>
            <Col xs="auto">
              <Button color="primary" onClick={onNewProcess} className="me-2">
                🔄 Try Again
              </Button>
              <Button color="secondary" onClick={onRestart}>
                🏠 New Analysis
              </Button>
            </Col>
          </Row>
        </CardBody>
      </Card>

      {/* Overall Score */}
      <Card className="mb-4">
        <CardBody className="text-center">
          <Row>
            <Col md={4}>
              <div className={`display-4 text-${getScoreColor(results.overall_adherence)}`}>
                {results.overall_adherence}%
              </div>
              <h5 className={`text-${getScoreColor(results.overall_adherence)}`}>
                {getScoreLabel(results.overall_adherence)}
              </h5>
              <p className="text-muted">Overall Adherence</p>
            </Col>
            
            <Col md={4}>
              <div className="h2">{results.completed_steps}/{results.total_steps}</div>
              <h6>Steps Completed</h6>
              <Progress 
                value={(results.completed_steps / results.total_steps) * 100}
                color={getScoreColor(results.completion_adherence)}
              />
            </Col>
            
            <Col md={4}>
              <div className="h2">{formatTime(results.total_time)}</div>
              <h6>Total Time</h6>
              <small className="text-muted">
                Target: {formatTime(results.target_total_time)}
              </small>
            </Col>
          </Row>
        </CardBody>
      </Card>

      {/* Detailed Metrics */}
      <Row className="mb-4">
        <Col md={6}>
          <Card className="h-100">
            <CardBody>
              <h6>Completion Metrics</h6>
              
              <div className="mb-3">
                <div className="d-flex justify-content-between mb-1">
                  <span>Step Completion</span>
                  <span>{results.completion_adherence}%</span>
                </div>
                <Progress value={results.completion_adherence} color={getScoreColor(results.completion_adherence)} />
              </div>

              <div className="mb-3">
                <div className="d-flex justify-content-between mb-1">
                  <span>Timing Accuracy</span>
                  <span>{results.timing_adherence}%</span>
                </div>
                <Progress value={results.timing_adherence} color={getScoreColor(results.timing_adherence)} />
              </div>

              <div className="row text-center">
                <div className="col-6">
                  <div className="border-end">
                    <div className="h4">{results.completed_steps}</div>
                    <small className="text-muted">Completed</small>
                  </div>
                </div>
                <div className="col-6">
                  <div className="h4">{results.total_steps - results.completed_steps}</div>
                  <small className="text-muted">Missed</small>
                </div>
              </div>
            </CardBody>
          </Card>
        </Col>

        <Col md={6}>
          <Card className="h-100">
            <CardBody>
              <h6>Timing Analysis</h6>
              
              <div className="mb-3">
                <Row className="text-center">
                  <Col>
                    <div className="h5 mb-0">{formatTime(results.total_time)}</div>
                    <small className="text-muted">Actual Time</small>
                  </Col>
                  <Col>
                    <div className="h5 mb-0">{formatTime(results.target_total_time)}</div>
                    <small className="text-muted">Target Time</small>
                  </Col>
                  <Col>
                    <div className={`h5 mb-0 text-${
                      results.total_time <= results.target_total_time ? 'success' : 'warning'
                    }`}>
                      {results.total_time > results.target_total_time ? '+' : ''}
                      {formatTime(Math.abs(results.total_time - results.target_total_time))}
                    </div>
                    <small className="text-muted">Difference</small>
                  </Col>
                </Row>
              </div>

              <div className="text-center">
                <div className={`badge bg-${
                  results.total_time <= results.target_total_time * 1.1 ? 'success' : 'warning'
                } fs-6`}>
                  {results.total_time <= results.target_total_time ? '🎯 Under Time' :
                   results.total_time <= results.target_total_time * 1.2 ? '⚠️ Slightly Over' : '🐌 Too Slow'}
                </div>
              </div>
            </CardBody>
          </Card>
        </Col>
      </Row>

      {/* Step-by-Step Breakdown */}
      <Card>
        <CardBody>
          <h6>Step-by-Step Analysis</h6>
          
          {results.step_details.length > 0 ? (
            <Table responsive>
              <thead>
                <tr>
                  <th>Step</th>
                  <th>Action</th>
                  <th>Time Taken</th>
                  <th>Target Time</th>
                  <th>Performance</th>
                </tr>
              </thead>
              <tbody>
                {results.step_details.map((step, index) => {
                  const timingStatus = getTimingStatus(step.duration, step.targetDuration);
                  
                  return (
                    <tr key={index}>
                      <td>
                        <span className="fw-bold">{step.stepNumber}</span>
                      </td>
                      <td>{step.stepName}</td>
                      <td>{step.duration.toFixed(1)}s</td>
                      <td>{step.targetDuration}s</td>
                      <td>
                        <span className={`badge bg-${timingStatus.color}`}>
                          {timingStatus.label}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          ) : (
            <div className="text-center p-4 text-muted">
              <p>No steps were completed during this session.</p>
              <small>Make sure to follow the process steps and interact with the designated zones.</small>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Recommendations */}
      <Card className="mt-4">
        <CardBody>
          <h6>Recommendations for Improvement</h6>
          <ul className="mb-0">
            {results.completion_adherence < 100 && (
              <li>Complete all process steps in the correct sequence</li>
            )}
            {results.timing_adherence < 80 && (
              <li>Practice to improve timing - aim for consistency with target times</li>
            )}
            {results.overall_adherence < 70 && (
              <li>Review the process steps and practice in a controlled environment</li>
            )}
            {results.overall_adherence >= 90 && (
              <li className="text-success">Excellent performance! Consider this your benchmark.</li>
            )}
          </ul>
        </CardBody>
      </Card>
    </div>
  );
};

export default ProcessResults;