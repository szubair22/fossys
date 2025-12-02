/// <reference path="../pb_data/types.d.ts" />

/**
 * Migration: Seed Default Meeting Templates
 * Creates global meeting templates for common organization types
 */

migrate((app) => {
  const templates = app.findCollectionByNameOrId("meeting_templates");

  // ========================================
  // Template 1: Fraternity/Sorority Chapter Meeting
  // ========================================
  const fraternityTemplate = new Record(templates, {
    name: "Fraternity/Sorority Chapter Meeting",
    org_type: "fraternity",
    description: "Standard chapter meeting format with roll call, officer reports, old/new business, and ritualistic closing.",
    default_meeting_title: "Chapter Meeting",
    default_meeting_type: "general",
    is_global: true,
    default_agenda: JSON.stringify([
      { title: "Call to Order", item_type: "topic", duration: 2, description: "Meeting called to order by presiding officer" },
      { title: "Roll Call", item_type: "topic", duration: 5, description: "Secretary takes attendance and confirms quorum" },
      { title: "Reading of Minutes", item_type: "topic", duration: 5, description: "Minutes from previous meeting read and approved" },
      { title: "Officer Reports", item_type: "topic", duration: 15, description: "Reports from chapter officers" },
      { title: "Committee Reports", item_type: "topic", duration: 10, description: "Updates from standing and special committees" },
      { title: "Old Business", item_type: "topic", duration: 15, description: "Continuation of business from previous meetings" },
      { title: "New Business", item_type: "motion", duration: 20, description: "Introduction and discussion of new items" },
      { title: "Good of the Order", item_type: "topic", duration: 10, description: "Announcements and general discussion" },
      { title: "Adjournment", item_type: "topic", duration: 2, description: "Motion to adjourn" }
    ]),
    settings: JSON.stringify({
      default_quorum: 50,
      quorum_type: "percentage",
      allow_proxy_voting: false
    })
  });
  app.save(fraternityTemplate);

  // ========================================
  // Template 2: HOA Board Meeting
  // ========================================
  const hoaTemplate = new Record(templates, {
    name: "HOA Board Meeting",
    org_type: "hoa",
    description: "Homeowners Association board meeting following Robert's Rules of Order.",
    default_meeting_title: "Board of Directors Meeting",
    default_meeting_type: "board",
    is_global: true,
    default_agenda: JSON.stringify([
      { title: "Call to Order", item_type: "topic", duration: 2, description: "President calls meeting to order" },
      { title: "Establish Quorum", item_type: "topic", duration: 2, description: "Confirm quorum of board members present" },
      { title: "Approval of Agenda", item_type: "motion", duration: 3, description: "Motion to approve or amend agenda" },
      { title: "Approval of Previous Minutes", item_type: "motion", duration: 5, description: "Motion to approve minutes from last meeting" },
      { title: "Financial Report", item_type: "topic", duration: 10, description: "Treasurer presents financial status" },
      { title: "Management Report", item_type: "topic", duration: 10, description: "Property manager updates" },
      { title: "Committee Reports", item_type: "topic", duration: 15, description: "Reports from architectural, landscape, and other committees" },
      { title: "Old Business", item_type: "topic", duration: 15, description: "Updates on ongoing matters" },
      { title: "New Business", item_type: "motion", duration: 20, description: "New motions and proposals" },
      { title: "Homeowner Forum", item_type: "topic", duration: 15, description: "Open forum for homeowner comments (non-voting)" },
      { title: "Executive Session", item_type: "topic", duration: 0, description: "Closed session for legal/personnel matters (if needed)" },
      { title: "Next Meeting Date", item_type: "topic", duration: 2, description: "Confirm date of next meeting" },
      { title: "Adjournment", item_type: "motion", duration: 2, description: "Motion to adjourn" }
    ]),
    settings: JSON.stringify({
      default_quorum: 3,
      quorum_type: "count",
      allow_proxy_voting: true,
      require_roll_call_votes: true
    })
  });
  app.save(hoaTemplate);

  // ========================================
  // Template 3: Nonprofit Board Meeting
  // ========================================
  const nonprofitTemplate = new Record(templates, {
    name: "Nonprofit Board Meeting",
    org_type: "nonprofit",
    description: "Standard nonprofit board meeting format with governance focus.",
    default_meeting_title: "Board of Directors Meeting",
    default_meeting_type: "board",
    is_global: true,
    default_agenda: JSON.stringify([
      { title: "Welcome and Call to Order", item_type: "topic", duration: 3, description: "Chair welcomes attendees and calls meeting to order" },
      { title: "Roll Call and Quorum", item_type: "topic", duration: 3, description: "Secretary confirms attendance and quorum" },
      { title: "Approval of Agenda", item_type: "motion", duration: 2, description: "Motion to approve agenda" },
      { title: "Consent Agenda", item_type: "motion", duration: 5, description: "Approve routine items (minutes, reports) as a package" },
      { title: "Executive Director Report", item_type: "topic", duration: 15, description: "ED presents organizational updates" },
      { title: "Financial Report", item_type: "topic", duration: 15, description: "Treasurer and Finance Committee report" },
      { title: "Committee Reports", item_type: "topic", duration: 20, description: "Standing committee updates" },
      { title: "Strategic Discussion", item_type: "topic", duration: 20, description: "Focus topic for board discussion" },
      { title: "Action Items", item_type: "motion", duration: 15, description: "Motions requiring board action" },
      { title: "Board Development", item_type: "topic", duration: 10, description: "Governance, recruitment, training updates" },
      { title: "Announcements", item_type: "topic", duration: 5, description: "Upcoming events and deadlines" },
      { title: "Executive Session", item_type: "topic", duration: 0, description: "Confidential matters (if needed)" },
      { title: "Adjournment", item_type: "motion", duration: 2, description: "Motion to adjourn" }
    ]),
    settings: JSON.stringify({
      default_quorum: 51,
      quorum_type: "percentage",
      allow_proxy_voting: false,
      conflict_of_interest_disclosure: true
    })
  });
  app.save(nonprofitTemplate);

  // ========================================
  // Template 4: Church Council Meeting
  // ========================================
  const churchTemplate = new Record(templates, {
    name: "Church Council Meeting",
    org_type: "church",
    description: "Church leadership council or vestry meeting format.",
    default_meeting_title: "Council Meeting",
    default_meeting_type: "committee",
    is_global: true,
    default_agenda: JSON.stringify([
      { title: "Opening Prayer", item_type: "topic", duration: 3, description: "Devotional and prayer" },
      { title: "Call to Order", item_type: "topic", duration: 2, description: "Chair calls meeting to order" },
      { title: "Attendance", item_type: "topic", duration: 2, description: "Note members present" },
      { title: "Approval of Minutes", item_type: "motion", duration: 5, description: "Review and approve previous minutes" },
      { title: "Pastor's Report", item_type: "topic", duration: 10, description: "Ministry updates from pastoral staff" },
      { title: "Financial Report", item_type: "topic", duration: 10, description: "Treasurer's report on finances" },
      { title: "Ministry Reports", item_type: "topic", duration: 15, description: "Updates from ministry areas" },
      { title: "Old Business", item_type: "topic", duration: 15, description: "Follow-up on previous items" },
      { title: "New Business", item_type: "motion", duration: 20, description: "New proposals and decisions" },
      { title: "Prayer Requests", item_type: "topic", duration: 5, description: "Share prayer concerns" },
      { title: "Closing Prayer", item_type: "topic", duration: 3, description: "Closing devotion" },
      { title: "Adjournment", item_type: "topic", duration: 2, description: "Meeting adjourned" }
    ]),
    settings: JSON.stringify({
      default_quorum: 50,
      quorum_type: "percentage"
    })
  });
  app.save(churchTemplate);

  // ========================================
  // Template 5: Corporate Board Meeting
  // ========================================
  const corporateTemplate = new Record(templates, {
    name: "Corporate Board Meeting",
    org_type: "corporate",
    description: "Formal corporate board meeting following standard governance practices.",
    default_meeting_title: "Board of Directors Meeting",
    default_meeting_type: "board",
    is_global: true,
    default_agenda: JSON.stringify([
      { title: "Call to Order", item_type: "topic", duration: 2, description: "Chairman calls meeting to order" },
      { title: "Quorum Determination", item_type: "topic", duration: 2, description: "Corporate Secretary confirms quorum" },
      { title: "Approval of Minutes", item_type: "motion", duration: 5, description: "Approve minutes of previous meeting" },
      { title: "CEO Report", item_type: "topic", duration: 20, description: "Chief Executive Officer's report" },
      { title: "CFO Report", item_type: "topic", duration: 15, description: "Financial performance and outlook" },
      { title: "Committee Reports", item_type: "topic", duration: 20, description: "Audit, Compensation, Governance committee reports" },
      { title: "Strategic Matters", item_type: "topic", duration: 30, description: "Discussion of strategic initiatives" },
      { title: "Resolutions", item_type: "motion", duration: 20, description: "Formal resolutions requiring board action" },
      { title: "Executive Session", item_type: "topic", duration: 0, description: "Confidential matters without management" },
      { title: "Other Business", item_type: "topic", duration: 10, description: "Any other matters" },
      { title: "Adjournment", item_type: "motion", duration: 2, description: "Motion to adjourn" }
    ]),
    settings: JSON.stringify({
      default_quorum: 50,
      quorum_type: "percentage",
      require_roll_call_votes: true,
      minutes_review_required: true
    })
  });
  app.save(corporateTemplate);

  // ========================================
  // Template 6: Generic Meeting
  // ========================================
  const genericTemplate = new Record(templates, {
    name: "General Meeting",
    org_type: "generic",
    description: "Simple meeting format suitable for any organization.",
    default_meeting_title: "Meeting",
    default_meeting_type: "general",
    is_global: true,
    default_agenda: JSON.stringify([
      { title: "Welcome", item_type: "topic", duration: 2, description: "Welcome attendees" },
      { title: "Attendance", item_type: "topic", duration: 3, description: "Note who is present" },
      { title: "Review Previous Minutes", item_type: "topic", duration: 5, description: "Review and approve previous minutes" },
      { title: "Updates", item_type: "topic", duration: 15, description: "Status updates and reports" },
      { title: "Discussion Items", item_type: "topic", duration: 30, description: "Main topics for discussion" },
      { title: "Action Items Review", item_type: "topic", duration: 10, description: "Review and assign action items" },
      { title: "Next Steps", item_type: "topic", duration: 5, description: "Confirm next meeting and follow-ups" },
      { title: "Close", item_type: "topic", duration: 2, description: "Meeting closed" }
    ]),
    settings: JSON.stringify({
      default_quorum: 0,
      quorum_type: "none"
    })
  });
  app.save(genericTemplate);

}, (app) => {
  // Rollback - delete seeded templates
  // Note: In production, you'd want to be more careful about this
  try {
    const templates = app.findCollectionByNameOrId("meeting_templates");
    const records = app.findRecordsByFilter(templates, "is_global = true", "", 100, 0);
    records.forEach(record => {
      app.delete(record);
    });
  } catch(e) {}
});
