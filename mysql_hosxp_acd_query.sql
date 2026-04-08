SELECT
    NULL AS id,
    (SELECT hospitalcode FROM opdconfig LIMIT 1) AS hoscode,
    (SELECT hospitalname FROM opdconfig LIMIT 1) AS hosname,
    p.hn AS hn,
    p.cid AS cid,
    CONCAT(p.pname, p.fname, ' ', p.lname) AS patient_name,
    v.vn AS vn,
    DATE_FORMAT(v.vstdate, '%Y-%m-%d') AS visit_date,
    TIME_FORMAT(v.vsttime, '%H:%i:%s') AS visit_time,
    CASE p.sex
        WHEN '1' THEN 'ชาย'
        WHEN '2' THEN 'หญิง'
        ELSE NULL
    END AS sex,
    TIMESTAMPDIFF(YEAR, p.birthday, v.vstdate) AS age,
    p.addrpart AS house_no,
    p.moopart AS moo,
    p.road AS road,
    t.name AS tumbon,
    a.name AS amphoe,
    c.name AS changwat,
    REPLACE(REPLACE(REPLACE(COALESCE(os.cc, er.er_list, ''), '\r', ' '), '\n', ' '), '|', '/') AS cc,
    IFNULL(el.er_emergency_level_name, NULL) AS triage,
    CASE ost.export_code
        WHEN '1' THEN 'กลับบ้าน'
        WHEN '2' THEN 'รับไว้รักษา'
        WHEN '3' THEN 'ส่งต่อ'
        WHEN '4' THEN 'เสียชีวิต'
        ELSE NULL
    END AS status,
    CONCAT(d1.icd10, '-', i1.name) AS pdx,
    CONCAT(d2.icd10, '-', i2.name) AS ext_dx,
    (
        SELECT CONCAT(
            '[',
            GROUP_CONCAT(
                DISTINCT JSON_OBJECT('code', d3.icd10, 'name', i3.name)
                ORDER BY d3.icd10
                SEPARATOR ','
            ),
            ']'
        )
        FROM ovstdiag d3
        JOIN icd101 i3 ON i3.code = d3.icd10
        WHERE d3.vn = v.vn
    ) AS dx_list,
    'auto' AS source,
    CASE WHEN aat.is_code = '1' THEN 1 ELSE 0 END AS alcohol,
    NULL AS cid_hash
FROM ovst v
JOIN patient p ON p.hn = v.hn
LEFT JOIN opdscreen os ON os.vn = v.vn
LEFT JOIN er_regist er ON er.vn = v.vn
LEFT JOIN er_emergency_level el ON el.er_emergency_level_id = er.er_emergency_level_id
LEFT JOIN ovstost ost ON ost.ovstost = v.ovstost
LEFT JOIN er_nursing_detail nd ON nd.vn = v.vn
LEFT JOIN accident_alcohol_type aat ON aat.accident_alcohol_type_id = nd.accident_alcohol_type_id
LEFT JOIN thaiaddress t
    ON t.chwpart = p.chwpart
    AND t.amppart = p.amppart
    AND t.tmbpart = p.tmbpart
    AND t.codetype = '3'
LEFT JOIN thaiaddress a
    ON a.chwpart = p.chwpart
    AND a.amppart = p.amppart
    AND a.tmbpart = '00'
    AND a.codetype = '2'
LEFT JOIN thaiaddress c
    ON c.chwpart = p.chwpart
    AND c.amppart = '00'
    AND c.tmbpart = '00'
    AND c.codetype = '1'
LEFT JOIN ovstdiag d1
    ON d1.vn = v.vn
    AND d1.diagtype = '1'
LEFT JOIN icd101 i1 ON i1.code = d1.icd10
LEFT JOIN ovstdiag d2
    ON d2.vn = v.vn
    AND d2.diagtype = '5'
LEFT JOIN icd101 i2 ON i2.code = d2.icd10
WHERE EXISTS (
    SELECT 1
    FROM ovstdiag d0
    WHERE d0.vn = v.vn
      AND d0.icd10 LIKE 'V%'
)
  AND v.vstdate >= '2026-01-01';
