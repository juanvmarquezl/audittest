select aa.code, aa.name, count(mv.id) as moves, 
       sum(mv.debit) as debit, sum(mv.credit) as credit
from account_move_line mv
left join account_account aa on mv.account_id = aa.id
where aa.reconcile = True and mv.reconcile_id is null
group by aa.code, aa.name
having count(mv.id) > 100 or sum(mv.debit) = sum(mv.credit)
order by aa.code